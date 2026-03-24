"""
Stage 02: Track Cutting (Manual or Auto Silence Detection)
REAL PROCESSING - Uses manual cut points from user or auto-detects silence
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging
import numpy as np
import soundfile as sf

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage02TrackCut(PipelineStage):
    def __init__(self):
        super().__init__(
            "02",
            "Track Cutting",
            "Manual cut points or silence detection",
        )

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"
        
        # Check if user provided manual cut points
        cut_points = context.get("config", {}).get("cut_points", [])
        skip_cutting = context.get("config", {}).get("skip_track_cutting", False)
        gate = context.get("config", {}).get("silence_gate", -50)
        min_silence = 0.8

        # If skip_cutting is True, just pass through the input
        if skip_cutting and not cut_points:
            self.log("info", "  ⊘ Track cutting skipped — using full audio")
            context["tracks"] = [input_path]
            context["cut_points"] = []
            self.status = "done"
            self.set_progress(100)
            return input_path

        self.log("cmd", f"$ python track_cut.py --input {input_path.name}")
        
        if cut_points:
            self.log("info", f"  using {len(cut_points)} manual cut points from user")
            for i, point in enumerate(cut_points):
                self.log("info", f"  cut @ {self._format_time(point)}")
        else:
            self.log("info", f"  scanning RMS envelope (gate: {gate}dB)...")

        # Load audio
        data, sr = await self._load_audio(input_path)
        self.log("info", f"  analyzing {len(data)/sr:.1f}s of audio...")

        # Detect silence if no manual cut points
        if not cut_points:
            cut_points = await self._detect_silence(data, sr, gate, min_silence)
            if not cut_points:
                self.log("info", "  no silence detected — using full audio as single track")
                context["tracks"] = [input_path]
                context["cut_points"] = []
                self.status = "done"
                self.set_progress(100)
                return input_path

        # Export tracks
        tracks_dir = input_path.parent / "tracks"
        tracks_dir.mkdir(exist_ok=True)

        track_paths = await self._export_tracks(input_path, data, sr, cut_points, tracks_dir)
        self.log("ok", f"  ✓ {len(track_paths)} tracks exported → track_01..{len(track_paths):02d}.wav")

        context["tracks"] = track_paths
        context["cut_points"] = cut_points

        self.status = "done"
        self.set_progress(100)
        return tracks_dir

    async def _load_audio(self, path: Path):
        """Load audio file using soundfile with scipy fallback"""
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        loop = asyncio.get_event_loop()
        try:
            data, sr = await loop.run_in_executor(None, sf.read, str(path))
            return data, sr
        except Exception as sf_err:
            logger.warning(f"soundfile failed ({sf_err}), trying scipy fallback...")
            try:
                from scipy.io import wavfile
                sr, data = await loop.run_in_executor(None, wavfile.read, str(path))
                data = data.astype(np.float32) / np.iinfo(data.dtype).max if data.dtype.kind == 'i' else data.astype(np.float32)
                return data, sr
            except Exception as scipy_err:
                raise RuntimeError(f"Cannot read audio file")

    def _compute_rms_envelope(self, data: np.ndarray, sr: int, window_ms: int = 10) -> np.ndarray:
        """Compute RMS envelope with specified window size"""
        window_size = int(sr * window_ms / 1000)
        rms = []
        for i in range(0, len(data), window_size):
            chunk = data[i:i + window_size]
            if len(chunk.shape) > 1:
                chunk = chunk.mean(axis=1)
            rms_val = np.sqrt(np.mean(chunk ** 2))
            rms.append(rms_val)
        return np.array(rms)

    async def _detect_silence(self, data: np.ndarray, sr: int, gate_db: float, min_silence_s: float) -> List[float]:
        """Detect silence regions and return cut points"""
        # Convert to mono if stereo
        if len(data.shape) > 1:
            mono = data.mean(axis=1)
        else:
            mono = data

        # Compute RMS envelope
        rms = self._compute_rms_envelope(mono, sr)

        # Convert gate to linear
        gate_linear = 10 ** (gate_db / 20)

        # Find silent regions
        silent = rms < gate_linear
        min_silence_samples = int(sr * min_silence_s)

        cut_points = []
        in_silence = False
        silence_start = 0

        for i, is_silent in enumerate(silent):
            if is_silent and not in_silence:
                in_silence = True
                silence_start = i
            elif not is_silent and in_silence:
                in_silence = False
                silence_duration = i - silence_start
                if silence_duration > len(silent) * (min_silence_s / (len(data) / sr)):
                    cut_point = (silence_start + i) / 2 * (len(data) / len(silent)) / sr
                    if 1.0 < cut_point < (len(data) / sr) - 1.0:  # Don't cut near edges
                        cut_points.append(cut_point)

        return cut_points[:10]  # Limit to 10 cut points max

    async def _export_tracks(self, path: Path, data: np.ndarray, sr: int, cut_points: List[float], output_dir: Path) -> List[Path]:
        """Split audio at cut points and export individual tracks"""
        track_paths = []
        points = [0.0] + sorted(cut_points) + [len(data) / sr]

        for i in range(len(points) - 1):
            track_path = output_dir / f"track_{i+1:02d}.wav"
            start_sample = int(points[i] * sr)
            end_sample = int(points[i + 1] * sr)

            track_data = data[start_sample:end_sample]

            # Write track file
            sf.write(str(track_path), track_data, sr)
            track_paths.append(track_path)

        return track_paths

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS.mmm"""
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:06.3f}"
