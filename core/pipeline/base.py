"""
Pipeline Stage Base Class
Single Responsibility: Define interface for all pipeline stages
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Base class for all pipeline stages"""

    def __init__(self, stage_num: str, name: str, description: str):
        self.stage_num = stage_num
        self.name = name
        self.description = description
        self.progress = 0.0
        self.status = "pending"  # pending, running, done, error
        self.logs: List[Dict[str, str]] = []

    @abstractmethod
    async def execute(self, input_path: Path, context: Dict[str, Any]) -> Path:
        """
        Execute the stage processing
        Args:
            input_path: Path to input file(s)
            context: Shared context dictionary with pipeline state
        Returns:
            Path to output file(s)
        """
        pass

    def log(self, level: str, message: str):
        """Add log entry"""
        entry = {"t": level, "m": message}
        self.logs.append(entry)
        logger.info(f"[Stage {self.stage_num}] {message}")

    def set_progress(self, percent: float):
        """Update progress (0-100)"""
        self.progress = max(0, min(100, percent))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize stage state for frontend"""
        return {
            "stage_num": self.stage_num,
            "name": self.name,
            "description": self.description,
            "progress": self.progress,
            "status": self.status,
            "logs": self.logs,
        }
