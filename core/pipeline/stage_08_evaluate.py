"""
Stage 08: Post-Mastering Evaluation
Quality Control - Measures final output LUFS, True-Peak, and Loudness Range (LRA)
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import re

from .base import PipelineStage

logger = logging.getLogger(__name__)


class Stage08Evaluate(PipelineStage):
    def __init__(self):
        super().__init__(
            "08",
            "Quality Assurance & Evaluation",
            "Measure final output LUFS · True-Peak · LRA report",
        )

    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        self.status = "running"
        exported_files = context.get("exported_files", [])
        
        # Find the primary lossless export (usually WAV)
        target_file = None
        for file_meta in exported_files:
            if file_meta.get("format", "").startswith("WAV"):
                target_file = Path(file_meta.get("path"))
                break
        
        # Fallback to FLAC if no WAV
        if not target_file:
            for file_meta in exported_files:
                if file_meta.get("format", "").startswith("FLAC"):
                    target_file = Path(file_meta.get("path"))
                    break
                    
        # If no lossless export to evaluate, just return
        if not target_file or not target_file.exists():
            self.log("warn", "  ⚠ No lossless output found to evaluate.")
            self.status = "done"
            self.set_progress(100)
            return input_path

        self.log("info", f"  evaluating master: {target_file.name}")
        self.log("cmd", f"$ ffmpeg -i {target_file.name} -filter_complex ebur128=peak=true -f null -")

        results = await self._run_ebur128(target_file)
        
        if results:
            lufs = results.get("I", -99.9)
            tp = results.get("Peak", -99.9)
            lra = results.get("LRA", 0.0)
            
            # Formatting the report
            self.log("ok", "  ────── MASTERING EVALUATION REPORT ──────")
            
            # Integrated LUFS
            lufs_target = context.get("studio_config", {}).get("target_lufs", -14.0)
            lufs_diff = lufs - lufs_target
            color = "ok" if abs(lufs_diff) <= 1.0 else "warn"
            self.log(color, f"  Integrated LUFS: {lufs:+.1f} (Target: {lufs_target:+.1f}, Error: {lufs_diff:+.1f})")
            
            # True Peak
            tp_limit = context.get("studio_config", {}).get("true_peak", -1.0)
            tp_margin = tp_limit - tp
            tp_color = "ok" if tp <= tp_limit + 0.1 else "err"
            self.log(tp_color, f"  Max True-Peak:   {tp:+.1f} dBTP (Limit: {tp_limit:+.1f}, Margin: {tp_margin:+.1f} dB)")
            
            # LRA
            lra_msg = f"  Loudness Range:  {lra:.1f} LU"
            if lra < 3.0:
                self.log("warn", lra_msg + " (Very compressed/squashed)")
            elif lra > 15.0:
                self.log("info", lra_msg + " (Highly dynamic)")
            else:
                self.log("info", lra_msg + " (Standard dynamics)")
                
            self.log("ok", "  ──────────────────────────────────────────")
            
            # Save the evaluation report to context
            context["evaluation_report"] = {
                "lufs_integrated": lufs,
                "lufs_target": lufs_target,
                "true_peak": tp,
                "true_peak_limit": tp_limit,
                "lra": lra,
                "file_evaluated": target_file.name
            }
        else:
            self.log("err", "  evaluation failed: could not parse ffprobe output")

        self.status = "done"
        self.set_progress(100)
        return target_file

    async def _run_ebur128(self, file_path: Path) -> Optional[Dict[str, float]]:
        """Run FFmpeg ebur128 filter and parse the output text."""
        cmd = [
            "ffmpeg",
            "-nostats",
            "-i", str(file_path),
            "-filter_complex", "ebur128=peak=true",
            "-f", "null",
            "-"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # ebur128 writes its results to stderr
            _, stderr = await process.communicate()
            output = stderr.decode('utf-8', errors='ignore')
            
            # Regex parsing - using findall and taking the latest/last match 
            # because FFmpeg prints intermediate status lines during processing.
            results = {}
            
            # Matches: I:         -14.3 LUFS
            matches_i = re.findall(r"I:\s+([-+]?\d*\.\d+|\d+)\s+LUFS", output)
            if matches_i:
                results["I"] = float(matches_i[-1])
                
            # Matches: LRA:         4.5 LU
            matches_lra = re.findall(r"LRA:\s+([-+]?\d*\.\d+|\d+)\s+LU", output)
            if matches_lra:
                results["LRA"] = float(matches_lra[-1])
                
            # Matches: Peak:       -1.0 dBFS (or dBTP if measured)
            matches_peak = re.findall(r"Peak:\s+([-+]?\d*\.\d+|\d+)\s+dB(?:FS|TP)", output)
            if matches_peak:
                results["Peak"] = float(matches_peak[-1])
                
            return results if results else None
            
        except Exception as e:
            logger.error(f"EBUR128 evaluation failed: {e}")
            return None
