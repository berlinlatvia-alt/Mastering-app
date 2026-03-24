"""
Pipeline Manager
Orchestrates all pipeline stages with progress tracking
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Callable
import logging

from .base import PipelineStage
from .stage_01_analysis import Stage01Analysis
from .stage_02_track_cut import Stage02TrackCut
from .stage_03_stem_sep import Stage03StemSeparation
from .stage_04_upmix import Stage04Upmix
from .stage_05_studio_chain import Stage05StudioChain
from .stage_06_loudness import Stage06Loudness
from .stage_07_encode import Stage07Encode

logger = logging.getLogger(__name__)


class PipelineManager:
    """Manages the complete 5.1 AutoMaster pipeline"""

    def __init__(self):
        self.stages: List[PipelineStage] = [
            Stage01Analysis(),
            Stage02TrackCut(),
            Stage03StemSeparation(),
            Stage04Upmix(),
            Stage05StudioChain(),
            Stage06Loudness(),
            Stage07Encode(),
        ]
        self.context: Dict[str, Any] = {}
        self.current_stage = 0
        self.is_running = False
        self.on_progress: Callable = None

    def configure(self, config: Dict[str, Any]):
        """Set pipeline configuration"""
        self.context["config"] = config
        logger.info(f"Pipeline configured: {config}")

    def set_studio_config(self, studio_config: Dict[str, Any]):
        """Set studio tuning configuration"""
        self.context["studio_config"] = studio_config
        logger.info(f"Studio config: {studio_config}")

    async def run(self, input_path: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Execute the complete pipeline
        Returns:
            Dictionary with results and exported files
        """
        if self.is_running:
            raise RuntimeError("Pipeline is already running")

        self.is_running = True
        self.current_stage = 0
        # Reset all stage states for a clean run
        for stage in self.stages:
            stage.progress = 0.0
            stage.status = "pending"
            stage.logs = []
        self.context["output_dir"] = output_dir
        self.context["input_path"] = input_path

        logger.info(f"Starting pipeline with input: {input_path}")

        try:
            current_path = input_path

            for i, stage in enumerate(self.stages):
                self.current_stage = i
                logger.info(f"Executing stage {stage.stage_num}: {stage.name}")

                if self.on_progress:
                    self.on_progress(i, stage.to_dict())

                current_path = await stage.execute(current_path, self.context)

                if self.on_progress:
                    self.on_progress(i, stage.to_dict())

            result = {
                "status": "complete",
                "output_dir": str(output_dir),
                "exported_files": self.context.get("exported_files", []),
                "stages": [s.to_dict() for s in self.stages],
            }

            logger.info("Pipeline completed successfully")
            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            # Mark the failing stage as error so the UI shows where it broke
            if self.current_stage < len(self.stages):
                self.stages[self.current_stage].status = "error"
                self.stages[self.current_stage].log("err", f"  ✗ stage failed: {e}")
            return {"status": "error", "error": str(e), "stage": self.current_stage}

        finally:
            self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            "is_running": self.is_running,
            "current_stage": self.current_stage,
            "stages": [s.to_dict() for s in self.stages],
            "context_keys": list(self.context.keys()),
            "exported_files": self.context.get("exported_files", []),
        }

    def reset(self):
        """Reset pipeline state"""
        self.current_stage = 0
        self.context = {}
        for stage in self.stages:
            stage.progress = 0
            stage.status = "pending"
            stage.logs = []
