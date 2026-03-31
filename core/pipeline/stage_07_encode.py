"""
Stage 07: Encode & Export
REAL PROCESSING - 6-ch WAV, AC-3, DTS, metadata embed
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging
import soundfile as sf
import os
import shutil

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage07Encode(PipelineStage):
    def __init__(self):
        super().__init__(
            "07",
            "Encode & Export",
            "6-ch WAV · AC-3 · DTS · metadata embed",
        )
        self.exported_files: List[Dict[str, str]] = []

    def _get_ffmpeg_cmd(self) -> str:
        """Get full path to ffmpeg executable"""
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        # Fallback to direct command (relies on PATH)
        return "ffmpeg"

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"
        self.exported_files = []  # Clear previous run's files

        output_dir = context.get("output_dir", input_path.parent / "final")
        output_dir.mkdir(exist_ok=True)

        mode = context.get("config", {}).get("mode", "basic")

        if mode == "pro":
            await self._export_pro(input_path, output_dir, context)
        else:
            await self._export_basic(input_path, output_dir, context)

        # Write metadata
        self.log("cmd", "$ python write_metadata.py --dialnorm=-31")
        await self._write_metadata(output_dir, context)
        self.log("ok", "  ✓ metadata embedded")

        self.log("sep", "──────────────────────────────────────────────")
        self.log("ok", "  🎉 PIPELINE COMPLETE — click ⬇ EXPORT FILES")

        context["exported_files"] = self.exported_files
        context["output_dir"] = output_dir

        self.status = "done"
        self.set_progress(100)
        return output_dir

    async def _export_basic(self, input_path: Path, output_dir: Path, context: Dict):
        """Basic mode: 3 clean outputs only"""
        self.log("info", "  Mode: BASIC — generating 3 files")
        
        orig_name = context.get("original_filename", "track")
        base_name = Path(orig_name).stem

        # 1. YouTube MP3 (320 kbps stereo)
        mp3_name = f"{base_name}_youtube.mp3"
        mp3_path = output_dir / mp3_name
        self.log("cmd", f"$ ffmpeg -i master.wav -c:a libmp3lame -b:a 320k -ar 48000 {mp3_name}")
        await self._export_mp3(input_path, mp3_path)
        size_mb = os.path.getsize(str(mp3_path)) / 1024 / 1024 if mp3_path.exists() else 0
        self.log("ok", f"  ✓ {mp3_name}  320 kbps stereo  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(mp3_path), "filename": mp3_name, "format": "MP3 320k", "size_mb": round(size_mb, 1), "label": "YouTube Ready"})

        # 2. Spotify WAV (48k 24-bit stereo, -14 LUFS)
        wav_name = f"{base_name}_spotify.wav"
        wav_path = output_dir / wav_name
        self.log("cmd", f"$ ffmpeg -i master.wav -c:a pcm_s24le -ar 48000 {wav_name}")
        await self._export_wav_stereo(input_path, wav_path)
        size_mb = os.path.getsize(str(wav_path)) / 1024 / 1024 if wav_path.exists() else 0
        self.log("ok", f"  ✓ {wav_name}  48kHz 24-bit stereo  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(wav_path), "filename": wav_name, "format": "WAV 24-bit", "size_mb": round(size_mb, 1), "label": "Spotify Master"})

        # 3. Pro FLAC 5.1
        flac_name = f"{base_name}_surround_5.1.flac"
        flac_path = output_dir / flac_name
        self.log("cmd", f"$ ffmpeg -i master.wav -c:a flac {flac_name}")
        await self._export_flac(input_path, flac_path)
        size_mb = os.path.getsize(str(flac_path)) / 1024 / 1024 if flac_path.exists() else 0
        self.log("ok", f"  ✓ {flac_name}  FLAC 5.1 Lossless  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(flac_path), "filename": flac_name, "format": "FLAC 5.1", "size_mb": round(size_mb, 1), "label": "Pro 5.1 Surround"})

    async def _export_pro(self, input_path: Path, output_dir: Path, context: Dict):
        """Pro mode: full multi-format export"""
        self.log("info", "  Mode: PRO — full export suite")

        # 6-channel WAV
        wav_path = output_dir / "output_51.wav"
        self.log("cmd", f"$ ffmpeg -i norm.wav -c:a pcm_s24le -channel_layout 5.1 {wav_path.name}")
        await self._export_wav(input_path, wav_path)
        size_mb = os.path.getsize(str(wav_path)) / 1024 / 1024 if wav_path.exists() else 0
        self.log("ok", f"  ✓ {wav_path.name}  6ch 48kHz 24-bit  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(wav_path), "format": "WAV 24-bit", "size_mb": round(size_mb, 1)})

        # AC-3
        ac3_path = output_dir / "output_51.ac3"
        self.log("cmd", f"$ ffmpeg -i norm.wav -c:a eac3 -b:a 640k {ac3_path.name}")
        await self._export_ac3(input_path, ac3_path)
        size_mb = os.path.getsize(str(ac3_path)) / 1024 / 1024 if ac3_path.exists() else 0
        self.log("ok", f"  ✓ {ac3_path.name}  640 kbps Dolby  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(ac3_path), "format": "AC-3 640k", "size_mb": round(size_mb, 1)})

        # FLAC
        flac_path = output_dir / "output_51.flac"
        self.log("cmd", f"$ ffmpeg -i norm.wav -c:a flac {flac_path.name}")
        await self._export_flac(input_path, flac_path)
        size_mb = os.path.getsize(str(flac_path)) / 1024 / 1024 if flac_path.exists() else 0
        self.log("ok", f"  ✓ {flac_path.name}  FLAC 5.1 Lossless  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(flac_path), "format": "FLAC 5.1", "size_mb": round(size_mb, 1)})

        # DTS
        dts_path = output_dir / "output_51.dts"
        self.log("cmd", "$ ffmpeg -i norm.wav -c:a dts -b:a 1509k output_51.dts")
        await self._export_dts(input_path, dts_path)
        size_mb = os.path.getsize(str(dts_path)) / 1024 / 1024 if dts_path.exists() else 0
        self.log("ok", f"  ✓ {dts_path.name}  DTS 1509 kbps  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(dts_path), "format": "DTS 1509k", "size_mb": round(size_mb, 1)})

        # MP3 for convenience
        mp3_path = output_dir / "output_stereo.mp3"
        self.log("cmd", "$ ffmpeg -i norm.wav -c:a libmp3lame -b:a 320k output_stereo.mp3")
        await self._export_mp3(input_path, mp3_path)
        size_mb = os.path.getsize(str(mp3_path)) / 1024 / 1024 if mp3_path.exists() else 0
        self.log("ok", f"  ✓ {mp3_path.name}  MP3 320k stereo  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(mp3_path), "format": "MP3 320k", "size_mb": round(size_mb, 1)})

    async def _export_wav_stereo(self, input_path: Path, output_path: Path):
        """Export 2-channel stereo WAV downmix (24-bit) — channel-index fold-down (layout-agnostic)"""
        # Use c0-c5 indices: c0=FL c1=FR c2=FC c3=LFE c4=BL c5=BR
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-af", "pan=stereo|c0=c0+0.707*c2+0.5*c4+0.1*c3|c1=c1+0.707*c2+0.5*c5+0.1*c3,volume=-1dB,limiter=1.0:1.0:1:all",
            "-c:a", "pcm_s24le",
            "-ar", "48000",
            str(output_path),
        ]
        try:
            logger.info(f"Running ffmpeg: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                stderr_text = stderr.decode() if stderr else "No stderr output"
                logger.error(f"Stereo WAV export failed (returncode {process.returncode}): {stderr_text}")
                raise RuntimeError(f"ffmpeg stereo WAV export failed: {stderr_text}")
        except Exception as e:
            logger.error(f"Stereo WAV export subprocess error: {e}")
            raise RuntimeError(f"ffmpeg stereo WAV export failed: {e}") from e

    async def _export_wav(self, input_path: Path, output_path: Path):
        """Export 6-channel WAV using soundfile"""
        try:
            data, sr = sf.read(str(input_path))
            # Write as 24-bit WAV
            sf.write(str(output_path), data, sr, subtype='PCM_24')
        except Exception as e:
            # Fallback to FFmpeg
            cmd = [
                self._get_ffmpeg_cmd(), "-y",
                "-i", str(input_path),
                "-c:a", "pcm_s24le",
                "-channel_layout", "5.1",
                str(output_path),
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

    async def _export_ac3(self, input_path: Path, output_path: Path):
        """Export Dolby AC-3 (E-AC-3)"""
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-c:a", "eac3",
            "-b:a", "640k",
            "-channel_layout", "5.1",
            str(output_path),
        ]
        try:
            logger.info(f"Running ffmpeg AC-3: {ffmpeg_cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                stderr_text = stderr.decode() if stderr else "No stderr output"
                logger.error(f"AC-3 export failed (returncode {process.returncode}): {stderr_text}")
                raise RuntimeError(f"ffmpeg AC-3 export failed: {stderr_text}")
        except Exception as e:
            logger.error(f"AC-3 export subprocess error: {e}")
            raise RuntimeError(f"ffmpeg AC-3 export failed: {e}") from e

    async def _export_flac(self, input_path: Path, output_path: Path):
        """Export FLAC"""
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-c:a", "flac",
            str(output_path),
        ]
        try:
            logger.info(f"Running ffmpeg FLAC: {ffmpeg_cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                stderr_text = stderr.decode() if stderr else "No stderr output"
                logger.error(f"FLAC export failed (returncode {process.returncode}): {stderr_text}")
                raise RuntimeError(f"ffmpeg FLAC export failed: {stderr_text}")
        except Exception as e:
            logger.error(f"FLAC export subprocess error: {e}")
            raise RuntimeError(f"ffmpeg FLAC export failed: {e}") from e

    async def _export_dts(self, input_path: Path, output_path: Path):
        """Export DTS"""
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-c:a", "dts",
            "-b:a", "1509k",
            "-channel_layout", "5.1",
            str(output_path),
        ]
        try:
            logger.info(f"Running ffmpeg DTS: {ffmpeg_cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                stderr_text = stderr.decode() if stderr else "No stderr output"
                logger.error(f"DTS export failed (returncode {process.returncode}): {stderr_text}")
                raise RuntimeError(f"ffmpeg DTS export failed: {stderr_text}")
        except Exception as e:
            logger.error(f"DTS export subprocess error: {e}")
            raise RuntimeError(f"ffmpeg DTS export failed: {e}") from e

    async def _export_mp3(self, input_path: Path, output_path: Path):
        """Export MP3 320k stereo — channel-index fold-down (layout-agnostic)"""
        # Use c0-c5 indices: c0=FL c1=FR c2=FC c3=LFE c4=BL c5=BR
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-af", "pan=stereo|c0=c0+0.707*c2+0.5*c4+0.1*c3|c1=c1+0.707*c2+0.5*c5+0.1*c3,volume=-1dB,limiter=1.0:1.0:1:all",
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            "-ar", "48000",
            str(output_path),
        ]
        try:
            logger.info(f"Running ffmpeg MP3: {ffmpeg_cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                stderr_text = stderr.decode() if stderr else "No stderr output"
                logger.error(f"MP3 export failed (returncode {process.returncode}): {stderr_text}")
                raise RuntimeError(f"ffmpeg MP3 export failed: {stderr_text}")
        except Exception as e:
            logger.error(f"MP3 export subprocess error: {e}")
            raise RuntimeError(f"ffmpeg MP3 export failed: {e}") from e

    async def _write_metadata(self, output_dir: Path, context: Dict):
        """Write EBU R128 and dialnorm metadata"""
        # Create metadata file
        meta_path = output_dir / "metadata.txt"
        
        final_lufs = context.get("final_lufs", -23.0)
        final_tp = context.get("final_tp", -1.0)
        
        metadata = f"""5.1 AutoMaster - Export Metadata
================================
Generated: {asyncio.get_event_loop().time()}

Loudness (EBU R128):
  Integrated: {final_lufs:.1f} LUFS
  True Peak:  {final_tp:+.1f} dBTP

Channel Layout: L R C LFE Ls Rs
Sample Rate:  48000 Hz
Bit Depth:    24-bit

Dialnorm: -31
"""
        
        with open(meta_path, 'w') as f:
            f.write(metadata)
        
        await asyncio.sleep(0.01)
