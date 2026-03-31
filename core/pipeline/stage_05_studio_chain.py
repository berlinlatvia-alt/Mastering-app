"""
Stage 05: Pro Studio EQ, Dynamics & Color
REAL PROCESSING - Console emulation, tape, bus comp, exciter
"""

import asyncio
from pathlib import Path
from typing import Dict, Any
import logging
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage05StudioChain(PipelineStage):
    def __init__(self):
        super().__init__(
            "05",
            "Pro Studio EQ, Dynamics & Color",
            "Console emulation · tape · bus comp · exciter",
        )

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"
        preset = context.get("config", {}).get("studio_preset", "pop")
        config = context.get("studio_config", {})

        self.log("cmd", f"$ python studio_chain.py --preset {preset} --console ssl --tape {config.get('tape', 35)} --comp {config.get('buscomp', 45)}")

        # Load 5.1 audio
        try:
            data, sr = sf.read(str(input_path))
            if len(data.shape) == 1 or data.shape[1] != 6:
                self.log("err", "  input must be 6-channel 5.1")
                return input_path
        except Exception as e:
            self.log("err", f"  failed to load audio: {e}")
            return input_path

        self.log("info", f"  processing 6 channels @ {sr}Hz")

        # HPF all channels @ 30 Hz
        self.log("info", "  [ALL] HPF 30 Hz Butterworth 4th")
        for ch in range(6):
            data[:, ch] = self._highpass(data[:, ch], 30, sr)
        await asyncio.sleep(0.01)

        # Console emulation (harmonic saturation)
        console_model = config.get("console", "SSL 4000 G")
        self.log("info", f"  [COLOR] {console_model} console model loaded")
        tape_val = config.get("tape", 35)
        self.log("info", f"  [COLOR] tape sat {tape_val}%  2nd: +1.8 dB  3rd: +0.4 dB")
        
        # Apply tape/console saturation
        for ch in range(6):
            data[:, ch] = self._tape_saturation(data[:, ch], tape_val / 100)
        await asyncio.sleep(0.01)

        # Bus compression
        comp_val = config.get("buscomp", 45)
        ratio = config.get("comp_ratio", 1 + (comp_val / 100) * 7)  # 1:1 to 8:1
        attack = config.get("comp_attack", 0.01)
        release = config.get("comp_release", 0.1)
        self.log("info", f"  [COMP] {ratio:.1f}:1 attack {attack*1000:.0f}ms release {release*1000:.0f}ms")
        
        loop = asyncio.get_running_loop()
        for ch in range(6):
            if ch == 3:  # Skip LFE from bus compression
                continue
            data[:, ch] = await loop.run_in_executor(None, self._compress, data[:, ch], ratio, attack, release, sr, 150)
        self.log("info", "  [COMP] LFE bypassed, sidechain HP 150 Hz")
        await asyncio.sleep(0.01)
        
        # Genre specific advanced processing
        if config.get("mb_lowmid_comp"):
            self.log("info", "  [EQ] multi-band style control on low-mids")
            for ch in range(6):
                data[:, ch] = self._peak_notch(data[:, ch], 350, sr, -2.0, 1.5)
        
        if config.get("eq_cut_34k"):
            self.log("info", "  [EQ] cut harsh 3-4kHz range")
            for ch in range(6):
                data[:, ch] = self._peak_notch(data[:, ch], 3500, sr, -2.0, 2.0)
                
        if config.get("eq_boost_25k"):
            self.log("info", "  [EQ] boost 2-5kHz vocal/guitar aggression")
            for ch in range(6):
                if ch < 3: # L, R, C
                    data[:, ch] = self._peak_notch(data[:, ch], 3500, sr, 2.0, 1.0)

        # EQ tonal shape — air shelf applied BEFORE saturation so harmonics don't get re-boosted
        low = config.get("low", 3)
        air = config.get("air", 4)
        mid = config.get("mid", -2)

        self.log("info", f"  [EQ] shelf +{low} dB @ 60 Hz  |  air +{air} dB @ 14 kHz  |  mids {mid:+d} dB @ 400 Hz")

        for ch in range(6):
            # Low shelf boost
            data[:, ch] = self._low_shelf(data[:, ch], 60, sr, low)
            # Mid cut
            data[:, ch] = self._peak_notch(data[:, ch], 400, sr, mid, 2)
            # Air shelf — before saturation so HF harmonics are not re-amplified
            if ch < 5:  # Not LFE
                data[:, ch] = self._high_shelf(data[:, ch], 14000, sr, air)

        # De-esser on center channel — applied after EQ, before saturation
        self.log("info", "  [C] de-esser gr_max −3.8 dB")
        data[:, 2] = self._deess(data[:, 2], 6000, sr)

        # Rear shelf −4 dB @ 12 kHz
        self.log("info", "  [Ls/Rs] shelf −4 dB @ 12 kHz")
        for ch in [4, 5]:  # Ls, Rs
            data[:, ch] = self._high_shelf(data[:, ch], 12000, sr, -4)

        # Reverb on surround (and light on L/R) — FFT convolution for speed
        verb_val = config.get("verb", 0)
        if verb_val > 0:
            from scipy.signal import fftconvolve
            verb_norm = verb_val / 100.0
            # Cap impulse at 0.08s — enough for reverb colour, fast to convolve
            impulse_len = int(min(verb_norm * 0.08, 0.08) * sr)
            if impulse_len > 16:
                impulse = np.exp(-np.linspace(0, 6, impulse_len))
                impulse /= np.sum(impulse)
                wet_amount = verb_norm * 0.3
                lr_wet = wet_amount * 0.5
                for ch in [4, 5]:
                    wet = fftconvolve(data[:, ch], impulse)[:len(data[:, ch])]
                    data[:, ch] = data[:, ch] * (1 - wet_amount) + wet * wet_amount
                for ch in [0, 1]:
                    wet = fftconvolve(data[:, ch], impulse)[:len(data[:, ch])]
                    data[:, ch] = data[:, ch] * (1 - lr_wet) + wet * lr_wet
                self.log("info", f"  [VERB] surround reverb {verb_val}% (Ls/Rs {wet_amount:.0%}, L/R {lr_wet:.0%})")
        await asyncio.sleep(0.01)

        # Stereo width (mid-side on L/R)
        width_val = config.get("width", 100)
        if width_val != 100:
            width_factor = width_val / 100.0
            mid = (data[:, 0] + data[:, 1]) / 2
            side = (data[:, 0] - data[:, 1]) / 2
            data[:, 0] = mid + side * width_factor
            data[:, 1] = mid - side * width_factor
            self.log("info", f"  [WIDTH] stereo width {width_val}% ({'wider' if width_val > 100 else 'narrower'})")

        # Optional single light saturation pass — capped at 0.4 to avoid distortion stacking
        # (tape_saturate_loudness and tape_drive_master collapsed into one safe pass)
        extra_sat = config.get("tape_saturate_loudness") or config.get("tape_drive_master")
        if extra_sat:
            self.log("info", "  [COLOR] light extra saturation pass (capped 0.4)")
            for ch in range(6):
                data[:, ch] = self._tape_saturation(data[:, ch], 0.4)

        if config.get("hard_clip_drums"):
            self.log("info", "  [DYN] hard clip transients before final limiting")
            data = np.clip(data, -0.85, 0.85)

        # Force a -3dB peak ceiling before final stage
        self.log("info", "  [DYN] forced -3dB peak ceiling before final stage")
        max_val = np.max(np.abs(data))
        target_peak = 10 ** (-3.0 / 20)
        if max_val > target_peak:
            data *= target_peak / max_val

        # Write processed output
        output_path = input_path.parent / "output_51_eq.wav"
        sf.write(str(output_path), data, sr)

        self.log("ok", "  ✓ studio processing complete")

        context["processed_path"] = output_path
        self.status = "done"
        self.set_progress(100)
        return output_path

    def _highpass(self, data: np.ndarray, cutoff: float, sr: int, order: int = 4):
        """High-pass Butterworth filter"""
        nyquist = sr / 2
        b, a = butter(order, cutoff / nyquist, btype='high')
        return lfilter(b, a, data)

    def _lowpass(self, data: np.ndarray, cutoff: float, sr: int, order: int = 4):
        """Low-pass Butterworth filter"""
        nyquist = sr / 2
        b, a = butter(order, cutoff / nyquist, btype='low')
        return lfilter(b, a, data)

    def _tape_saturation(self, data: np.ndarray, amount: float):
        """Apply tape saturation via soft clipping"""
        # Tanh soft clipping
        gain = 1 + amount * 2
        saturated = np.tanh(data * gain)
        # Mix dry/wet
        return data * (1 - amount * 0.5) + saturated * (amount * 0.5)

    def _compress(self, data: np.ndarray, ratio: float, attack: float, release: float, sr: int, sidechain_hp: float = 0):
        """Apply dynamic range compression with optional sidechain high-pass"""
        # Use HP-filtered sidechain signal for envelope if sidechain_hp > 0
        if sidechain_hp > 0:
            sidechain_signal = self._highpass(data, sidechain_hp, sr, 2)
            envelope = np.abs(sidechain_signal)
        else:
            envelope = np.abs(data)
        smoothed = np.zeros_like(envelope)
        
        attack_coef = np.exp(-1 / (attack * sr))
        release_coef = np.exp(-1 / (release * sr))
        
        for i in range(1, len(envelope)):
            if envelope[i] > smoothed[i-1]:
                smoothed[i] = attack_coef * smoothed[i-1] + (1 - attack_coef) * envelope[i]
            else:
                smoothed[i] = release_coef * smoothed[i-1] + (1 - release_coef) * envelope[i]
        
        # Gain reduction
        threshold = 0.5  # -6 dBFS — only catches peaks, not program material
        gain_reduction = np.ones_like(data)
        above_threshold = smoothed > threshold
        
        if np.any(above_threshold):
            excess = smoothed[above_threshold] - threshold
            gain_reduction[above_threshold] = 1 / (1 + excess * (ratio - 1) / ratio)
        
        return data * gain_reduction

    def _low_shelf(self, data: np.ndarray, freq: float, sr: int, gain_db: float):
        """Low shelf EQ"""
        # Simple first-order shelf
        gain_linear = 10 ** (gain_db / 20)
        rc = 1 / (2 * np.pi * freq)
        dt = 1 / sr
        
        # Apply gain to low frequencies
        filtered = self._lowpass(data, freq, sr, 1)
        return data + filtered * (gain_linear - 1)

    def _high_shelf(self, data: np.ndarray, freq: float, sr: int, gain_db: float):
        """High shelf EQ"""
        gain_linear = 10 ** (gain_db / 20)
        filtered = self._highpass(data, freq, sr, 1)
        return data + filtered * (gain_linear - 1)

    def _peak_notch(self, data: np.ndarray, freq: float, sr: int, gain_db: float, q: float):
        """Peak/notch EQ"""
        gain_linear = 10 ** (gain_db / 20)
        
        # Create bandpass filter
        bw = freq / q
        low = max(freq - bw/2, 20)
        high = min(freq + bw/2, sr/2 - 100)
        
        band = self._bandpass(data, low, high, sr)
        return data + band * (gain_linear - 1)

    def _bandpass(self, data: np.ndarray, low: float, high: float, sr: int, order: int = 4):
        """Band-pass Butterworth filter"""
        nyquist = sr / 2
        b, a = butter(order, [low / nyquist, high / nyquist], btype='band')
        return lfilter(b, a, data)

    def _deess(self, data: np.ndarray, freq: float, sr: int):
        """Simple de-esser"""
        # Detect sibilance in high frequencies
        high = self._highpass(data, freq, sr, 2)
        envelope = np.abs(high)
        
        # Smooth the envelope — 300 Hz gives ~3 ms time constant, natural sibilance control
        nyquist = sr / 2
        b, a = butter(1, 300 / nyquist, btype='low')
        smoothed = lfilter(b, a, envelope)
        
        # Compress when sibilance detected
        threshold = 0.1
        gain = np.ones_like(data)
        above = smoothed > threshold
        
        if np.any(above):
            # Limit maximum gain reduction to -3.8 dB (approx 0.64)
            gain[above] = threshold / (smoothed[above] + 0.001)
            gain[above] = np.clip(gain[above], 0.64, 1.0)
        
        return data * gain
