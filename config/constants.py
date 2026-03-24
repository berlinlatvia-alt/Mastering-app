"""
5.1 AutoMaster - Configuration & Constants
DOGE Mode: Hardware-first reasoning, minimal waste
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure directories exist
for d in [OUTPUT_DIR, TEMP_DIR, UPLOAD_DIR]:
    d.mkdir(exist_ok=True)

# Audio processing defaults
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BIT_DEPTH = 24
DEFAULT_TARGET_LUFS = -14.0  # Spotify / streaming standard (EBU R128 broadcast = -23.0)
DEFAULT_TRUE_PEAK_LIMIT = -1.0  # dBTP
DEFAULT_SILENCE_GATE = -50  # dBFS
DEFAULT_MIN_SILENCE_DURATION = 0.8  # seconds
DEFAULT_LFE_CROSSOVER = 80  # Hz

# Stem separation models
STEM_MODELS = {
    "htdemucs_6s": {
        "stems": ["vocals", "drums", "bass", "guitar", "piano", "other"],
        "vram_gb": 6.0,
        "ram_gb": 4.0,
    },
    "htdemucs_ft": {
        "stems": ["vocals", "drums", "bass", "other"],
        "vram_gb": 5.0,
        "ram_gb": 3.5,
    },
    "spleeter_5stems": {
        "stems": ["vocals", "drums", "bass", "piano", "other"],
        "vram_gb": 4.0,
        "ram_gb": 3.0,
    },
}

# Export formats
EXPORT_FORMATS = {
    "wav_48k_24bit": {
        "codec": "pcm_s24le",
        "sample_rate": 48000,
        "bit_depth": 24,
        "extension": ".wav",
        "lossless": True,
    },
    "flac_6ch": {
        "codec": "flac",
        "sample_rate": 48000,
        "bit_depth": 24,
        "extension": ".flac",
        "lossless": True,
    },
    "ac3_640k": {
        "codec": "eac3",
        "bitrate": "640k",
        "sample_rate": 48000,
        "extension": ".ac3",
        "lossless": False,
    },
    "dts_1509k": {
        "codec": "dts",
        "bitrate": "1509k",
        "sample_rate": 48000,
        "extension": ".dts",
        "lossless": False,
    },
}

# Studio tuning presets (from frontend)
STUDIO_PRESETS = {
    "pop": {
        "tape": 35,
        "harm": 20,
        "buscomp": 45,
        "trans": 55,
        "para": 25,
        "low": 3,
        "mid": -2,
        "air": 4,
        "sub": 60,
        "width": 100,
        "rear": 40,
        "verb": 30,
        "lfe": 80,
    },
    "rock": {
        "tape": 60,
        "harm": 45,
        "buscomp": 65,
        "trans": 75,
        "para": 40,
        "low": 6,
        "mid": 2,
        "air": 2,
        "sub": 75,
        "width": 110,
        "rear": 35,
        "verb": 20,
        "lfe": 80,
    },
    "electronic": {
        "tape": 10,
        "harm": 5,
        "buscomp": 55,
        "trans": 80,
        "para": 50,
        "low": 8,
        "mid": -4,
        "air": 8,
        "sub": 85,
        "width": 130,
        "rear": 55,
        "verb": 25,
        "lfe": 90,
    },
    "jazz": {
        "tape": 45,
        "harm": 30,
        "buscomp": 25,
        "trans": 30,
        "para": 10,
        "low": 1,
        "mid": 1,
        "air": 3,
        "sub": 40,
        "width": 90,
        "rear": 50,
        "verb": 55,
        "lfe": 70,
    },
    "hiphop": {
        "tape": 25,
        "harm": 35,
        "buscomp": 70,
        "trans": 85,
        "para": 60,
        "low": 9,
        "mid": -3,
        "air": 5,
        "sub": 90,
        "width": 105,
        "rear": 30,
        "verb": 15,
        "lfe": 100,
    },
    "rnb": {
        "tape": 45,
        "harm": 30,
        "buscomp": 25,
        "trans": 40,
        "para": 15,
        "low": 4,
        "mid": 0,
        "air": 3,
        "sub": 65,
        "width": 110,
        "rear": 50,
        "verb": 40,
        "lfe": 85,
    },
    "afrobeats": {
        "tape": 40,
        "harm": 40,
        "buscomp": 55,
        "trans": 65,
        "para": 45,
        "low": 7,
        "mid": 2,
        "air": 4,
        "sub": 75,
        "width": 100,
        "rear": 45,
        "verb": 30,
        "lfe": 90,
    },
    "cinematic": {
        "tape": 50,
        "harm": 25,
        "buscomp": 35,
        "trans": 45,
        "para": 20,
        "low": 4,
        "mid": -1,
        "air": 6,
        "sub": 65,
        "width": 120,
        "rear": 70,
        "verb": 65,
        "lfe": 80,
    },
    "spotify_pop": {
        "tape": 20,
        "harm": 15,
        "buscomp": 45,
        "trans": 60,
        "para": 30,
        "low": 2,
        "mid": -1,
        "air": 6,
        "sub": 50,
        "width": 105,
        "rear": 35,
        "verb": 25,
        "lfe": 80,
        "target_lufs": -8.5,
        "true_peak": -1.0,
        "mb_lowmid_comp": True,
        "comp_attack": 0.005,
        "comp_release": 0.05,
    },
    "spotify_hiphop": {
        "tape": 30,
        "harm": 35,
        "buscomp": 70,
        "trans": 85,
        "para": 60,
        "low": 7,
        "mid": -2,
        "air": 4,
        "sub": 95,
        "width": 100,
        "rear": 30,
        "verb": 15,
        "lfe": 100,
        "target_lufs": -9.0,
        "true_peak": -1.0,
        "comp_attack": 0.035,
        "comp_release": 0.1,
        "hard_clip_drums": True,
    },
    "spotify_rb": {
        "tape": 45,
        "harm": 30,
        "buscomp": 25,
        "trans": 40,
        "para": 15,
        "low": 4,
        "mid": 0,
        "air": 3,
        "sub": 65,
        "width": 110,
        "rear": 50,
        "verb": 40,
        "lfe": 85,
        "target_lufs": -10.5,
        "true_peak": -1.0,
        "comp_ratio": 2.0,
        "eq_cut_34k": True,
        "tape_saturate_loudness": True,
    },
    "spotify_rock": {
        "tape": 65,
        "harm": 45,
        "buscomp": 60,
        "trans": 70,
        "para": 40,
        "low": 5,
        "mid": 2,
        "air": 3,
        "sub": 70,
        "width": 115,
        "rear": 45,
        "verb": 25,
        "lfe": 80,
        "target_lufs": -8.0,
        "true_peak": -1.0,
        "comp_attack": 0.01,
        "comp_release": 0.05,
        "eq_boost_25k": True,
        "tape_drive_master": True,
    },
}

# Channel assignments for 5.1
CHANNEL_LAYOUT_51 = ["L", "R", "C", "LFE", "Ls", "Rs"]
CHANNEL_ORDER_FFMPEG = "5.1"  # ITU-R BS.775

# Server configuration
HOST = "127.0.0.1"
PORT = 8000
MAX_UPLOAD_SIZE_MB = 500
REQUEST_TIMEOUT_SEC = 300

# Logging
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
