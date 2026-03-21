"""Pipeline package for 5.1 AutoMaster"""
from .base import PipelineStage
from .manager import PipelineManager
from .stage_01_analysis import Stage01Analysis
from .stage_02_track_cut import Stage02TrackCut
from .stage_03_stem_sep import Stage03StemSeparation
from .stage_04_upmix import Stage04Upmix
from .stage_05_studio_chain import Stage05StudioChain
from .stage_06_loudness import Stage06Loudness
from .stage_07_encode import Stage07Encode

__all__ = [
    "PipelineStage",
    "PipelineManager",
    "Stage01Analysis",
    "Stage02TrackCut",
    "Stage03StemSeparation",
    "Stage04Upmix",
    "Stage05StudioChain",
    "Stage06Loudness",
    "Stage07Encode",
]
