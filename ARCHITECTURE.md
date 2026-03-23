# Architecture Documentation

## System Overview

5.1 AutoMaster is a **localhost-first** audio mastering pipeline that converts stereo Suno tracks into professional 5.1 surround sound.

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  app.js     │  │  pipeline.js│  │  tuning.js              │ │
│  │  (entry)    │  │  (stages)   │  │  (studio config)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │  api.js     │  │  export.js  │                              │
│  │  (HTTP)     │  │  (download) │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP/JSON
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (main.py)                               │   │
│  │  - REST endpoints                                        │   │
│  │  - File upload/download                                  │   │
│  │  - Hardware monitoring                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pipeline Manager                                       │   │
│  │  - Stage orchestration                                  │   │
│  │  - Progress tracking                                    │   │
│  │  - Context sharing                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │Stage 01 │ │Stage 02 │ │Stage 03 │ │Stage 04 │ │Stage 05 │  │
│  │Analysis │ │TrackCut │ │Stem Sep │ │Upmix    │ │Studio   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│  ┌─────────┐ ┌─────────┐                                       │
│  │Stage 06 │ │Stage 07 │                                       │
│  │Loudness │ │Encode   │                                       │
│  └─────────┘ └─────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↕ subprocess
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL TOOLS                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  FFmpeg      │  │  Demucs      │  │  PyTorch (CUDA)      │  │
│  │  - resample  │  │  - stems     │  │  - GPU acceleration  │  │
│  │  - encode    │  │  - separation│  │  - tensor ops        │  │
│  │  - loudness  │  │  - htdemucs  │  │  - VRAM management   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. File Upload

```
User drops file → Frontend reads file → POST /api/upload
                  ↓
Backend saves to uploads/{session_id}/
                  ↓
Returns session_id to frontend
```

### 2. Pipeline Execution

```
POST /api/run → PipelineManager.run()
                  ↓
              For each stage:
                  ↓
              stage.execute(input_path, context)
                  ↓
              - subprocess calls (FFmpeg, Demucs)
              - Progress updates
              - Log entries
                  ↓
              Returns output_path
                  ↓
              Next stage receives output_path as input
```

### 3. Progress Polling

```
Frontend polls /api/status every 500ms
                  ↓
Backend returns:
{
  is_running: bool,
  current_stage: int,
  stages: [
    { status: "running", progress: 45, logs: [...] },
    ...
  ]
}
                  ↓
Frontend updates UI (stage card, sidebar, console)
```

### 4. Export

```
User clicks "EXPORT FILES" → ExportUI.show()
                  ↓
User selects files → clicks "Export Selected"
                  ↓
Frontend generates manifest .txt
                  ↓
Downloads manifest + triggers file downloads
```

---

## Module Responsibilities

### Frontend Modules

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `app.js` | Application lifecycle, event binding, coordination | ~200 |
| `api.js` | HTTP client, request/response handling | ~100 |
| `pipeline.js` | Stage visualization, progress, waveform | ~300 |
| `tuning.js` | Studio parameters, presets, sliders | ~150 |
| `export.js` | File selection, quick presets, manifest | ~200 |

### Backend Modules

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `main.py` | FastAPI routes, file I/O, session management | ~250 |
| `base.py` | PipelineStage interface, logging, progress | ~50 |
| `manager.py` | Stage orchestration, context sharing | ~100 |
| `stage_01*.py` | Audio analysis, resampling, LUFS | ~120 |
| `stage_02*.py` | Silence detection, track splitting | ~100 |
| `stage_03*.py` | Demucs integration, GPU management | ~80 |
| `stage_04*.py` | 5.1 channel routing, upmixing | ~100 |
| `stage_05*.py` | DSP chain (EQ, compression, saturation) | ~100 |
| `stage_06*.py` | EBU R128 normalization | ~100 |
| `stage_07*.py` | Encoding (WAV, AC-3, DTS) | ~120 |

---

## Configuration Flow

```
User changes slider → tuning.js updates local config
                          ↓
              Debounced (300ms) → API.configureStudio()
                          ↓
              Backend: pipeline.set_studio_config()
                          ↓
              Stored in context["studio_config"]
                          ↓
              Stage 05 reads config during execution
```

---

## Hardware Monitoring

### RAM Monitoring (psutil)

```python
ram = psutil.virtual_memory()
ram_percent = ram.percent
ram_used_gb = ram.used / 1024**3
```

### VRAM Monitoring (PyTorch)

```python
if torch.cuda.is_available():
    vram_used = torch.cuda.memory_allocated(0) / 1024**3
    vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    vram_percent = (vram_used / vram_total) * 100
```

### Frontend Display

- Updates every 2 seconds via `/api/hardware`
- Shows RAM bar (orange) and VRAM bar (blue)
- Displays numeric values in GB

---

## Error Handling

### Frontend

```javascript
try {
  await this.api.runPipeline();
} catch (error) {
  this.log('err', `Pipeline failed: ${error.message}`);
  // UI reverts to idle state
}
```

### Backend

```python
try:
    result = await pipeline.run(input_path, output_dir)
except Exception as e:
    logger.error(f"Pipeline failed: {e}", exc_info=True)
    return {"status": "error", "error": str(e)}
```

### Fail-Fast Policy

- Missing dependencies → immediate error message
- GPU OOM → fallback to CPU with warning
- File format invalid → reject before processing

---

## Security Considerations

1. **Localhost Only** — Server binds to `127.0.0.1`, not public IP
2. **No Authentication** — Assumes local trust boundary
3. **File Validation** — Checks extensions (.wav, .flac, .aiff)
4. **Size Limits** — MAX_UPLOAD_SIZE_MB = 500
5. **Path Sanitization** — Uses pathlib, no user-controlled paths

---

## Performance Optimizations

1. **Async I/O** — All file operations use asyncio
2. **GPU Acceleration** — Demucs runs on CUDA when available
3. **Progressive Rendering** — UI updates per-stage, not per-step
4. **Debounced Config** — Studio tuning sends updates after 300ms idle
5. **Efficient Polling** — 500ms interval balances responsiveness vs load

---

## Testing Strategy

### Manual Testing Checklist

- [ ] Upload WAV file (44.1 kHz, 16-bit)
- [ ] Upload FLAC file (48 kHz, 24-bit)
- [ ] Run pipeline with default config
- [ ] Apply studio preset (rock)
- [ ] Adjust tape saturation slider
- [ ] Export all recommended files
- [ ] Download individual file

### Automated Testing (Future)

```bash
# Run stress test
python tests/stress_test.py

# Verify pipeline stages
python tests/test_pipeline.py

# Check API endpoints
python tests/test_api.py
```

---

## Changelog

- **Spotify Genre Presets**: Added `spotify_pop`, `spotify_hiphop`, `spotify_rb`, `spotify_rock` to `constants.py` with custom dynamic control/EQ processing rules in `stage_05_studio_chain.py`.
- **FLAC Output Support**: Modified `stage_06_loudness.py` and `stage_07_encode.py` to add bypass mechanisms for aggressive mastering presets when a lossless FLAC target format is requested.

---

## Future Enhancements

1. **Atmos Export** — Dolby Atmos renderer (requires separate license)
2. **Batch Processing** — Queue multiple tracks
3. **A/B Comparison** — Toggle between original and processed
4. **Plugin Support** — VST3/AU plugin integration
5. **Cloud Sync** — Optional upload to cloud storage

---

**Last Updated**: March 20, 2026  
**Author**: Generation Null
