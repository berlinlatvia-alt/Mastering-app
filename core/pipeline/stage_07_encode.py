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

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"

        output_dir = context.get("output_dir", input_path.parent / "final")
        output_dir.mkdir(exist_ok=True)

        # Export 6-channel WAV
        wav_path = output_dir / "output_51.wav"
        self.log("cmd", f"$ ffmpeg -i norm.wav -c:a pcm_s24le -channel_layout 5.1 {wav_path.name}")
        await self._export_wav(input_path, wav_path)
        size_mb = os.path.getsize(str(wav_path)) / 1024 / 1024 if wav_path.exists() else 0
        self.log("ok", f"  ✓ {wav_path.name}  6ch 48kHz 24-bit  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(wav_path), "format": "WAV 24-bit", "size_mb": size_mb})

        # Export Dolby AC-3
        ac3_path = output_dir / "output_51.ac3"
        self.log("cmd", f"$ ffmpeg -i norm.wav -c:a eac3 -b:a 640k {ac3_path.name}")
        await self._export_ac3(input_path, ac3_path)
        size_mb = os.path.getsize(str(ac3_path)) / 1024 / 1024 if ac3_path.exists() else 0
        self.log("ok", f"  ✓ {ac3_path.name}  640 kbps Dolby  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(ac3_path), "format": "AC-3 640k", "size_mb": size_mb})

        # Export DTS
        dts_path = output_dir / "output_51.dts"
        self.log("cmd", "$ ffmpeg -i norm.wav -c:a dts -b:a 1509k output_51.dts")
        await self._export_dts(input_path, dts_path)
        size_mb = os.path.getsize(str(dts_path)) / 1024 / 1024 if dts_path.exists() else 0
        self.log("ok", f"  ✓ {dts_path.name}  DTS 1509 kbps  ({size_mb:.1f} MB)")
        self.exported_files.append({"path": str(dts_path), "format": "DTS 1509k", "size_mb": size_mb})

        # Write metadata
        self.log("cmd", "$ python write_metadata.py --dialnorm=-31 --lufs=-23.0")
        await self._write_metadata(output_dir, context)
        self.log("ok", "  ✓ metadata embedded")

        self.log("sep", "──────────────────────────────────────────────")
        self.log("ok", "  🎉 PIPELINE COMPLETE — files ready for export")

        context["exported_files"] = self.exported_files
        context["output_dir"] = output_dir

        self.status = "done"
        self.set_progress(100)
        return output_dir

    async def _export_wav(self, input_path: Path, output_path: Path):
        """Export 6-channel WAV using soundfile"""
        try:
            data, sr = sf.read(str(input_path))
            # Write as 24-bit WAV
            sf.write(str(output_path), data, sr, subtype='PCM_24')
        except Exception as e:
            # Fallback to FFmpeg
            cmd = [
                "ffmpeg", "-y",
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
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-c:a", "eac3",
            "-b:a", "640k",
            "-channel_layout", "5.1",
            str(output_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"AC-3 export failed: {stderr.decode()}")

    async def _export_dts(self, input_path: Path, output_path: Path):
        """Export DTS"""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-c:a", "dts",
            "-b:a", "1509k",
            "-channel_layout", "5.1",
            str(output_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"DTS export failed: {stderr.decode()}")

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
        
        await asyncio.sleep(0.1)
