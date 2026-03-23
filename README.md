# 5.1 AutoMaster — Suno to Surround

**Fully automatic 5.1 mastering pipeline for localhost deployment**

---

## Architecture

```
mastering-app/
├── backend/
│   └── main.py              # FastAPI server (entry point)
├── core/
│   └── pipeline/
│       ├── base.py          # Pipeline stage interface
│       ├── manager.py       # Pipeline orchestrator
│       ├── stage_01_analysis.py
│       ├── stage_02_track_cut.py
│       ├── stage_03_stem_sep.py
│       ├── stage_04_upmix.py
│       ├── stage_05_studio_chain.py
│       ├── stage_06_loudness.py
│       └── stage_07_encode.py
├── config/
│   └── constants.py         # Configuration & presets
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js           # Main entry point
│       ├── api.js           # HTTP client
│       ├── pipeline.js      # Pipeline UI
│       ├── tuning.js        # Studio tuning
│       └── export.js        # Export manager
├── output/                  # Generated files
├── temp/                    # Processing temp files
├── uploads/                 # Uploaded audio files
├── requirements.txt
└── start.bat
```

---

## DOGE Mode Principles

This codebase follows **DOGE Mode** engineering principles:

1. **Zero-Defect Code** — Full implementations, no placeholders
2. **Hardware-First Reasoning** — Memory-aware processing, GPU optimization
3. **Engineering Minimalism** — Single responsibility modules (<500 lines)
4. **Fail-Fast Policy** — Immediate error reporting with fallbacks
5. **Modular Architecture** — Separation of concerns (config/core/services)

---

## Quick Start

### Prerequisites

- **Python 3.10+** (64-bit)
- **FFmpeg** (for audio processing)
- **8+ GB RAM** (16 GB recommended)
- **NVIDIA GPU** (optional, for GPU acceleration)

### Installation

1. **Clone or download** this repository

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (if not already installed):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, add `bin/` to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

4. **Install Demucs** (for stem separation):
   ```bash
   pip install -U demucs
   ```

### Running the Server

**Option 1: Use the startup script** (Windows)
```bash
start.bat
```

**Option 2: Manual start**
```bash
python backend\main.py
```

**Option 3: With uvicorn directly**
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access the Application

Open your browser to:
```
http://127.0.0.1:8000
```

---

## Pipeline Stages

| Stage | Name | Processing | Resources |
|-------|------|------------|-----------|
| **01** | Input Preparation & Analysis | Resample, normalize, spectral scan, true-peak detection | CPU, ~0.5 GB RAM |
| **02** | Track Cutting | RMS envelope, silence detection, zero-crossing alignment | CPU, ~1 GB RAM |
| **03** | Stem Separation | Demucs v4 htdemucs_6s, 6 stems, GPU accelerated | GPU (6-8 GB VRAM), ~6 GB RAM |
| **04** | 5.1 Upmix | Channel assignment, pan law, LFE crossover | CPU, ~4 GB RAM |
| **05** | Studio Chain | Console emulation, tape, bus comp, EQ, exciter | CPU, ~5 GB RAM |
| **06** | Loudness Normalization | EBU R128, integrated LUFS, true-peak | CPU, ~2 GB RAM |
| **07** | Encode & Export | 6-ch WAV, AC-3, DTS, metadata embed | CPU, ~3 GB RAM |

---

## Features

### Studio Tuning

Access via **⚙ Studio Tuning** button (top-right):

- **Genre Presets**: Pop, Rock, Electronic, Jazz, Hip-Hop, Cinematic
- **Analog Color**: Tape saturation, harmonic drive, console emulation
- **Dynamics**: Bus compression, transient punch, parallel crush
- **Tonal Shape**: Low-end punch, mid presence, air/sparkle
- **5.1 Spatial**: Stereo width, rear depth, room reverb, LFE crossover

### Export Groups

Files are organized by playback destination:

1. **🗄 Archival** — Lossless masters for studio handoff
2. **🚗 Car Audio** — Dolby AC-3 / DTS for head units
3. **🎧 Headphones** — Binaural HRTF renders for IEMs
4. **🎵 Fan Downloads** — FLAC/MP3 for Bandcamp stores
5. **📡 Streaming** — Stereo downmix for DSPs

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve frontend |
| `GET` | `/api/status` | Get pipeline status |
| `GET` | `/api/hardware` | Get hardware utilization |
| `POST` | `/api/upload` | Upload audio file |
| `POST` | `/api/configure` | Configure pipeline |
| `POST` | `/api/studio-config` | Set studio tuning |
| `POST` | `/api/studio-preset/{name}` | Apply studio preset |
| `POST` | `/api/run` | Start pipeline |
| `GET` | `/api/export/{session_id}` | Get exported files |
| `GET` | `/api/download/{session_id}/{filename}` | Download file |

---

## Configuration

Edit `config/constants.py` to customize:

```python
# Audio defaults
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BIT_DEPTH = 24
DEFAULT_TARGET_LUFS = -23.0  # EBU R128
DEFAULT_TRUE_PEAK_LIMIT = -1.0  # dBTP
DEFAULT_LFE_CROSSOVER = 80  # Hz

# Server
HOST = "127.0.0.1"
PORT = 8000
MAX_UPLOAD_SIZE_MB = 500
```

---

## Troubleshooting

### "FFmpeg not found"
- Ensure FFmpeg is installed and in your system PATH
- Restart terminal after adding to PATH
- Verify with: `ffmpeg -version`

### "CUDA out of memory"
- Reduce batch size or use CPU mode
- Close other GPU applications
- Use smaller stem model: `htdemucs_ft`

### "Port 8000 already in use"
- Kill existing process: `taskkill /F /IM python.exe`
- Or change port in `backend/main.py`

### Slow processing
- GPU acceleration requires NVIDIA GPU with 6+ GB VRAM
- CPU-only mode is significantly slower for stem separation
- Ensure adequate RAM (16 GB recommended)

---

## Project Structure Rules

Following **DOGE Mode** standards:

- **Files < 500 lines** — Refactor if larger
- **Functions < 50 lines** — Extract complex logic
- **Single responsibility** — Each module does ONE thing well
- **No placeholders** — Full implementations only
- **Comments for WHY** — Code explains what, comments explain why

---

## Changelog

- **Added Spotify Genre Presets**: Pop, Hip-Hop, R&B, and Rock configurations strictly targeting Spotify's streaming LUFS/TP standards with genre-specific mastering chain settings (multi-band compression, tailored EQ, hard clipping).
- **FLAC Lossless Output Support**: FLAC 5.1 export option is natively supported in the UI, which intentionally bypasses Spotify's aggressive loudness targeting rules in Stage 06 to preserve full dynamic range.

---

## License

MIT License — See LICENSE file

---

## Credits

Built with:
- **FastAPI** — Modern Python web framework
- **Demucs** — State-of-the-art music source separation
- **FFmpeg** — Audio processing powerhouse
- **PyTorch** — GPU-accelerated tensor operations

---

**Last Updated**: March 20, 2026  
**Version**: 1.0.0
