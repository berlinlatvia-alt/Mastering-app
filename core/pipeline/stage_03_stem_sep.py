"""
Stage 03: Stem Separation (Demucs v4)
REAL PROCESSING - htdemucs_6s, 6 stems, GPU accelerated
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging
import os
import soundfile as sf

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage03StemSeparation(PipelineStage):
    def __init__(self):
        super().__init__(
            "03",
            "Stem Separation",
            "Demucs v4 · 6 stems",
        )
        self.stem_names = ["vocals", "drums", "bass", "guitar", "piano", "other"]

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"
        model_name = context.get("config", {}).get("stem_model", "htdemucs_6s")
        
        self.log("cmd", f"$ demucs --model {model_name} {input_path.name}")

        stems_dir = input_path.parent / "stems"
        stems_dir.mkdir(exist_ok=True)

        stem_paths = {}

        # Try Demucs separation
        try:
            stem_paths = await self._separate_stems(input_path, stems_dir, model_name)
            self.log("ok", f"  ✓ {len(stem_paths)} stems separated")
        except Exception as e:
            self.log("warn", f"  stem separation failed: {e}")
            self.log("info", "  falling back to direct audio split (no Demucs)")
            # Use the original uploaded file, not the tracks directory from stage 02
            source_file = context.get("input_path", input_path)
            stem_paths = await self._fallback_split(source_file, stems_dir)
            self.log("ok", f"  ✓ {len(stem_paths)} stems created from source audio")

        context["stems"] = stem_paths
        context["stem_dir"] = stems_dir

        self.status = "done"
        self.set_progress(100)
        return stems_dir

    async def _separate_stems(self, input_path: Path, stems_dir: Path, model_name: str) -> Dict[str, Path]:
        """Separate audio into stems using Demucs v4"""
        try:
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
            from demucs.audio import AudioFile, save_audio
            import torch
        except ImportError as e:
            raise RuntimeError(f"Demucs not installed: {e}")

        # Get device
        device = self._get_device()
        self.log("info", f"  device: {device}")

        # Load model (fall back from 6s to 4-stem if unavailable)
        self.log("info", f"  loading model: {model_name}")
        try:
            model = get_model(model_name)
        except Exception as e:
            self.log("warn", f"  failed to load {model_name}, trying htdemucs")
            model = get_model("htdemucs")

        model.eval()

        # Load audio using Demucs v4 AudioFile API
        self.log("info", "  loading audio...")
        wav = AudioFile(str(input_path)).read(
            streams=0,
            samplerate=model.samplerate,
            channels=model.audio_channels,
        )  # shape: [channels, time]

        # Normalise: compute mean amplitude for denorm later
        ref = wav.mean(0)
        wav_mean = ref.mean()
        wav_std = ref.std()
        wav = (wav - wav_mean) / (wav_std + 1e-8)

        # Separate using apply_model (the correct Demucs v4 API)
        self.log("info", "  separating stems...")
        self.set_progress(30)

        with torch.no_grad():
            wav_t = wav.unsqueeze(0)  # [1, C, T]
            sources = apply_model(model, wav_t, device=device, progress=False)
            sources = sources[0]  # [stems, C, T]

        # Denormalise
        sources = sources * (wav_std + 1e-8) + wav_mean

        self.set_progress(70)

        # Save each stem
        stem_paths = {}
        sources_list = model.sources if hasattr(model, "sources") else self.stem_names

        for idx, name in enumerate(sources_list):
            if idx < sources.shape[0]:
                stem_path = stems_dir / f"{name}.wav"
                # Save with soundfile (avoids torchcodec dependency)
                stem_np = sources[idx].cpu().numpy()
                if stem_np.ndim == 2:
                    stem_np = stem_np.T  # (channels, samples) → (samples, channels)
                sf.write(str(stem_path), stem_np, model.samplerate)
                self.log("info", f"  {name + '.wav':12s} exported")
                stem_paths[name] = stem_path
                self.set_progress(70 + (20 * (idx + 1) / len(sources_list)))

        return stem_paths

    async def _fallback_split(self, input_path: Path, stems_dir: Path) -> Dict[str, Path]:
        """
        When Demucs is unavailable, use frequency-based splitting to create
        pseudo-stems that won't cause bass buildup in the 5.1 upmix.
        """
        import numpy as np
        from scipy.signal import butter, sosfilt

        loop = asyncio.get_event_loop()
        data, sr = await loop.run_in_executor(None, sf.read, str(input_path))

        # Ensure stereo
        if len(data.shape) == 1:
            data = np.column_stack([data, data])

        left  = data[:, 0]
        right = data[:, 1]
        mid   = (left + right) / 2
        side  = (left - right) / 2

        # Frequency-based filters
        def lowpass(sig, freq):
            sos = butter(4, freq, btype='low', fs=sr, output='sos')
            return sosfilt(sos, sig)

        def highpass(sig, freq):
            sos = butter(4, freq, btype='high', fs=sr, output='sos')
            return sosfilt(sos, sig)

        def bandpass(sig, low, high):
            sos = butter(4, [low, high], btype='band', fs=sr, output='sos')
            return sosfilt(sos, sig)

        # Bass: only sub-200Hz content from the mono center
        bass_mono = lowpass(mid, 200)

        # Vocals: mid-range center content (200Hz-6kHz)
        vocal_mono = bandpass(mid, 200, 6000)

        # Drums: transient/attack content — full range but emphasize 80Hz-8kHz
        drums_l = bandpass(left, 80, 8000)
        drums_r = bandpass(right, 80, 8000)

        # Guitar: mid-high stereo content (400Hz-8kHz)
        guitar_l = bandpass(left, 400, 8000)
        guitar_r = bandpass(right, 400, 8000)

        # Piano: high-mid side content (300Hz-5kHz)
        piano_side = bandpass(side, 300, 5000)

        # Other: high frequencies + ambient (above 6kHz)
        other_l = highpass(left, 6000) * 0.5
        other_r = highpass(right, 6000) * 0.5

        stem_signals = {
            "vocals": np.column_stack([vocal_mono, vocal_mono]),
            "drums":  np.column_stack([drums_l, drums_r]),
            "bass":   np.column_stack([bass_mono, bass_mono]),
            "guitar": np.column_stack([guitar_l, guitar_r]),
            "piano":  np.column_stack([piano_side, -piano_side]),
            "other":  np.column_stack([other_l, other_r]),
        }

        stem_paths: Dict[str, Path] = {}
        for name, signal in stem_signals.items():
            path = stems_dir / f"{name}.wav"
            await loop.run_in_executor(None, sf.write, str(path), signal.astype(np.float32), sr)
            stem_paths[name] = path
            self.log("info", f"  {name + '.wav':12s} split from source")

        return stem_paths

    def _get_device(self) -> str:
        """Get available compute device"""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
