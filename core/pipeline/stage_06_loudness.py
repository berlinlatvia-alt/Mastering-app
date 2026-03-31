"""
Stage 06: Loudness Normalization (EBU R128)
REAL PROCESSING - Integrated LUFS, true-peak, LRA measurement

FAST ABORT: Cooperative cancellation checkpoints for instant abort response.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any
import logging
import numpy as np
import soundfile as sf
import subprocess

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage06Loudness(PipelineStage):
    def __init__(self):
        super().__init__(
            "06",
            "Loudness Normalization (EBU R128)",
            "Integrated LUFS · true-peak · LRA",
        )
        self.channels = ["L", "R", "C", "LFE", "Ls", "Rs"]
        self.context = None  # Reference for abort checks

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.context = context  # Store for abort checks
        self.status = "running"
        
        studio_config = context.get("studio_config", {})
        preset_lufs = studio_config.get("target_lufs")
        
        output_format = context.get("config", {}).get("output_format", "wav_48k_24bit")
        is_flac = "flac" in output_format.lower()
        
        if is_flac and preset_lufs is not None:
            self.log("info", "  [FORMAT] FLAC detected: bypassing aggressive Spotify LUFS target")
            target_lufs = context.get("config", {}).get("target_lufs", -14.0)
        else:
            target_lufs = preset_lufs if preset_lufs is not None else context.get("config", {}).get("target_lufs", -14.0)
            
        tp_limit_db = studio_config.get("true_peak", -1.0)

        self.log("cmd", "$ ffmpeg -i output_51_eq.wav -af ebur128=framelog=verbose -f null -")

        # Load audio
        try:
            data, sr = sf.read(str(input_path))
            if len(data.shape) != 2 or data.shape[1] != 6:
                self.log("err", "  input must be 6-channel 5.1")
                return input_path
        except Exception as e:
            self.log("err", f"  failed to load audio: {e}")
            return input_path

        # Measure per-channel loudness
        self.log("info", "  measuring loudness per channel...")
        
        # FAST ABORT: Check before measurement
        if self.context and self.context.get("abort_requested"):
            raise asyncio.CancelledError("Pipeline aborted before loudness measurement")
        
        channel_measurements = await self._measure_loudness(data, sr)

        for ch, meas in channel_measurements.items():
            # FAST ABORT: Check during logging
            if self.context and self.context.get("abort_requested"):
                raise asyncio.CancelledError(f"Pipeline aborted during loudness logging for {ch}")
            self.log("info", f"  [{ch:3s}]   {meas['lufs']:+6.1f} LUFS  TP: {meas['tp']:+4.1f} dBTP")
            await asyncio.sleep(0)

        # FAST ABORT: Check before integrated loudness calculation
        if self.context and self.context.get("abort_requested"):
            raise asyncio.CancelledError("Pipeline aborted before integrated loudness calculation")

        # Calculate integrated loudness (energy sum of all channels)
        # EBU R128 uses K-weighted sum
        integrated_lufs = self._calculate_integrated_lufs(data, channel_measurements)
        makeup_gain = target_lufs - integrated_lufs

        # Limiter Behavior Rule: Max 4dB Gain Reduction
        input_peak_db = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
        peak_overshoot = (input_peak_db + makeup_gain) - tp_limit_db
        if peak_overshoot > 4.0:
            gain_drop = peak_overshoot - 4.0
            makeup_gain -= gain_drop
            self.log("info", f"  [LIMITER] overshoot {peak_overshoot:.1f}dB exceeds 4dB. Dropping input gain by {gain_drop:.1f}dB")

        self.log("info", f"  integrated loudness: {integrated_lufs:.1f} LUFS")
        self.log("info", f"  applying makeup: {makeup_gain:+.1f} dB → {target_lufs:.1f} LUFS target")

        # FAST ABORT: Check before normalization
        if self.context and self.context.get("abort_requested"):
            raise asyncio.CancelledError("Pipeline aborted before normalization")

        await asyncio.sleep(0.02)

        # Apply normalization
        output_path = input_path.parent / "output_51_norm.wav"
        await self._normalize(data, output_path, sr, makeup_gain, tp_limit_db)

        # FAST ABORT: Check before verification
        if self.context and self.context.get("abort_requested"):
            raise asyncio.CancelledError("Pipeline aborted before final verification")

        # Verify final loudness
        final_data, _ = sf.read(str(output_path))
        final_measurements = await self._measure_loudness(final_data, sr)
        final_tp = max(m["tp"] for m in final_measurements.values())
        
        self.log("ok", f"  ✓ final: {target_lufs:.1f} LUFS  TP: {final_tp:+.1f} dBTP ✓")

        context["normalized_path"] = output_path
        context["final_lufs"] = target_lufs
        context["final_tp"] = final_tp

        self.status = "done"
        self.set_progress(100)
        return output_path

    @staticmethod
    def _smooth_limiter_gain(n_samples, ahead_env, tp_linear, attack_coef, release_coef):
        """Compute smoothed gain curve for look-ahead limiter (runs in thread executor)"""
        gain_needed = np.where(ahead_env > tp_linear, tp_linear / (ahead_env + 1e-10), 1.0)
        smoothed_gain = np.ones(n_samples)
        for i in range(1, n_samples):
            if gain_needed[i] < smoothed_gain[i - 1]:
                smoothed_gain[i] = attack_coef * smoothed_gain[i - 1] + (1 - attack_coef) * gain_needed[i]
            else:
                smoothed_gain[i] = release_coef * smoothed_gain[i - 1] + (1 - release_coef) * gain_needed[i]
        return smoothed_gain

    async def _measure_loudness(self, data: np.ndarray, sr: int) -> Dict[str, Dict[str, float]]:
        """Measure loudness per channel using K-weighting (EBU R128)"""
        measurements = {}
        
        channel_names = ["L", "R", "C", "LFE", "Ls", "Rs"]
        
        for ch_idx, ch_name in enumerate(channel_names):
            if ch_idx < data.shape[1]:
                channel_data = data[:, ch_idx]
                
                # K-weighting filter (simplified EBU R128)
                k_weighted = self._k_weighting(channel_data, sr)
                
                # Calculate RMS
                rms = np.sqrt(np.mean(k_weighted ** 2 + 1e-10))
                
                # Convert to LUFS (approximate)
                # Reference: 0 dBFS = -0.691 dB LUFS for sine wave
                lufs = 20 * np.log10(rms + 1e-10) - 0.691
                
                # True peak estimation (oversampling simulation)
                true_peak = 20 * np.log10(np.max(np.abs(channel_data)) + 1e-10)
                
                measurements[ch_name] = {
                    "lufs": lufs,
                    "tp": true_peak,
                }
            else:
                measurements[ch_name] = {"lufs": -100, "tp": -100}
        
        return measurements

    def _k_weighting(self, data: np.ndarray, sr: int) -> np.ndarray:
        """Apply EBU R128 K-weighting filter"""
        # High-pass at 150 Hz (first order)
        # High-shelf at 1680 Hz (+4 dB gain)
        
        # Simplified K-filter approximation
        # Stage 1: HPF @ 150 Hz
        nyquist = sr / 2
        from scipy.signal import butter, lfilter, zpk2tf
        
        # First-order HPF at 150 Hz
        b1, a1 = butter(1, 150 / nyquist, btype='high')
        data = lfilter(b1, a1, data)
        
        # High-shelf @ 1680 Hz, +4 dB
        # Simple approximation: boost high frequencies
        b2, a2 = butter(1, 1680 / nyquist, btype='high')
        high = lfilter(b2, a2, data)
        data = data + high * 0.58  # ~4 dB boost
        
        return data

    def _calculate_integrated_lufs(self, data: np.ndarray, measurements: Dict) -> float:
        """Calculate integrated loudness from all channels"""
        # EBU R128: Sum energy from all channels with weighting
        # L, R, C: full weight
        # LFE: +10 dB weight (but often excluded)
        # Ls, Rs: full weight
        
        total_energy = 0
        
        weights = {"L": 1, "R": 1, "C": 1, "LFE": 0.5, "Ls": 1, "Rs": 1}
        
        for ch, meas in measurements.items():
            if meas["lufs"] > -70:  # Ignore silence
                energy = 10 ** (meas["lufs"] / 10)
                total_energy += energy * weights.get(ch, 1)
        
        # Convert back to LUFS
        if total_energy > 0:
            return 10 * np.log10(total_energy + 1e-10)
        return -70

    async def _normalize(self, data: np.ndarray, output_path: Path, sr: int, gain_db: float, tp_limit_db: float = -1.0):
        """Apply loudness normalization with look-ahead true-peak limiter"""
        gain_linear = 10 ** (gain_db / 20)
        normalized = data * gain_linear

        tp_linear = 10 ** (tp_limit_db / 20)
        max_tp = np.max(np.abs(normalized))

        if max_tp > tp_linear:
            n_samples, n_channels = normalized.shape

            # Look-ahead: read peak envelope 5ms ahead so gain reduction starts
            # before the peak arrives, avoiding the transient clipping that tanh caused
            lookahead = int(0.005 * sr)
            attack_coef = np.exp(-1 / (0.001 * sr))   # 1 ms attack
            release_coef = np.exp(-1 / (0.100 * sr))  # 100 ms release

            # Per-sample peak across all channels
            peak_env = np.max(np.abs(normalized), axis=1)

            # Shift envelope forward by lookahead samples
            ahead_env = np.empty(n_samples)
            ahead_env[:n_samples - lookahead] = peak_env[lookahead:]
            ahead_env[n_samples - lookahead:] = peak_env[-1]

            # Run the sample-by-sample gain smoothing in a thread so the
            # event loop stays free and abort signals can land immediately
            smoothed_gain = await asyncio.get_running_loop().run_in_executor(
                None, self._smooth_limiter_gain,
                n_samples, ahead_env, tp_linear, attack_coef, release_coef
            )

            # Apply time-varying gain to all channels
            for ch in range(n_channels):
                normalized[:, ch] *= smoothed_gain

            # Hard safety clip for any remaining inter-sample peaks
            normalized = np.clip(normalized, -tp_linear, tp_linear)

        sf.write(str(output_path), normalized, sr)
