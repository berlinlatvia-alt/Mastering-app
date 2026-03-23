# 5.1 AutoMaster - Quick Reference

## 🚀 Start Server

```bash
# Windows - Double click
start.bat

# Or command line
python backend\main.py
```

## 🌐 Access

```
http://127.0.0.1:8000
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend |
| `/api/status` | GET | Pipeline status |
| `/api/hardware` | GET | Hardware monitoring |
| `/api/upload` | POST | Upload audio |
| `/api/configure` | POST | Configure pipeline |
| `/api/studio-config` | POST | Studio tuning |
| `/api/studio-preset/{name}` | POST | Apply preset |
| `/api/run` | POST | Start pipeline |
| `/api/export/{session_id}` | GET | Get exports |
| `/api/download/{session_id}/{filename}` | GET | Download file |

## 🎛️ Pipeline Stages

| Stage | Name | Processing |
|-------|------|------------|
| 01 | Analysis | Resample, normalize, LUFS, true-peak |
| 02 | Track Cut | Silence detection, split tracks |
| 03 | Stem Sep | Demucs htdemucs_6s, 6 stems |
| 04 | Upmix | 5.1 channel assignment |
| 05 | Studio | EQ, compression, saturation |
| 06 | Loudness | EBU R128 normalization |
| 07 | Encode | WAV, AC-3, DTS export |

## 🎚️ Studio Presets

- **Pop** - Balanced, radio-ready
- **Rock** - Aggressive, punchy
- **Electronic** - Heavy bass, wide
- **Jazz** - Natural, dynamic
- **Hip-Hop** - Bass-heavy, compressed
- **Cinematic** - Wide, spacious

## 📁 Directory Structure

```
mastering-app/
├── backend/         # Server
├── core/pipeline/   # Processing stages
├── config/          # Configuration
├── frontend/        # UI
├── output/          # Exported files
├── temp/            # Temp files
└── uploads/         # Uploaded files
```

## ⚙️ Configuration

Edit `config/constants.py`:

```python
DEFAULT_TARGET_LUFS = -23.0  # EBU R128
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BIT_DEPTH = 24
MAX_UPLOAD_SIZE_MB = 500
```

## 🔧 Troubleshooting

### Server won't start
```bash
pip install -r requirements.txt
```

### FFmpeg not found
Download from ffmpeg.org, add to PATH

### Port 8000 in use
```bash
taskkill /F /IM python.exe
```

### GPU OOM
Close other GPU apps, use CPU mode

## 📊 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| VRAM | 0 GB | 8 GB |
| Storage | 1 GB free | 10 GB free |
| CPU | 4 cores | 8 cores |

## 🎯 Export Formats

- **WAV 24-bit** - Lossless master
- **FLAC 6ch** - Lossless compressed
- **AC-3 640k** - Dolby Digital (car)
- **DTS 1509k** - DTS (premium)

## 📖 Documentation

- `README.md` - User guide
- `ARCHITECTURE.md` - Technical docs
- `DEPLOYMENT_SUMMARY.md` - Deployment
- `SOLUTION_SUMMARY.md` - Solution overview

## 🛠️ Development

### Run in dev mode
```bash
uvicorn backend.main:app --reload
```

### Check imports
```bash
python -c "from backend.main import app"
```

### Test API
```bash
curl http://127.0.0.1:8000/api/status
```

---

**Version**: 1.0.0 | **Status**: ✅ Production Ready
