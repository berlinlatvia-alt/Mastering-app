"""
5.1 AutoMaster - FastAPI Server
Main entry point for localhost deployment
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
from pathlib import Path
import logging
import uuid
import psutil
import shutil

# Optional imports (fail gracefully if not available)
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from config import OUTPUT_DIR, TEMP_DIR, UPLOAD_DIR, STUDIO_PRESETS
from core.pipeline import PipelineManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="5.1 AutoMaster",
    description="Suno to Surround - Automatic 5.1 Mastering Pipeline",
    version="1.0.0",
)

# CORS for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline = PipelineManager()
active_sessions: Dict[str, Dict] = {}


# ============ Models ============


class PipelineConfig(BaseModel):
    target_lufs: float = -14.0  # Spotify streaming target
    stem_model: str = "htdemucs_6s"
    silence_gate: int = -50
    output_format: str = "wav_48k_24bit"
    studio_preset: str = "pop"


class StudioConfig(BaseModel):
    tape: int = 35
    harm: int = 20
    buscomp: int = 45
    trans: int = 55
    para: int = 25
    low: int = 3
    mid: int = -2
    air: int = 4
    sub: int = 60
    width: int = 100
    rear: int = 40
    verb: int = 30
    lfe: int = 80
    console: str = "SSL 4000 G"


class StatusResponse(BaseModel):
    is_running: bool
    current_stage: int
    stages: List[Dict]
    session_id: Optional[str] = None


class HardwareStatus(BaseModel):
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    vram_percent: float = 0.0
    vram_used_gb: float = 0.0
    vram_total_gb: float = 0.0


# ============ Routes ============


@app.get("/")
async def root():
    """Serve the frontend"""
    return FileResponse("frontend/index.html")


@app.get("/api/status")
async def get_status() -> StatusResponse:
    """Get pipeline status"""
    status = pipeline.get_status()
    session_id = list(active_sessions.keys())[-1] if active_sessions else None
    return StatusResponse(**status, session_id=session_id)


@app.get("/api/hardware")
async def get_hardware() -> HardwareStatus:
    """Get hardware utilization"""
    ram = psutil.virtual_memory()
    hw = HardwareStatus(
        ram_percent=ram.percent,
        ram_used_gb=round(ram.used / 1024**3, 2),
        ram_total_gb=round(ram.total / 1024**3, 2),
    )

    if TORCH_AVAILABLE and torch.cuda.is_available():
        hw.vram_used_gb = round(torch.cuda.memory_allocated(0) / 1024**3, 2)
        hw.vram_total_gb = round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
        )
        hw.vram_percent = round(
            (hw.vram_used_gb / hw.vram_total_gb) * 100, 1
        )

    return hw


@app.post("/api/upload")
async def upload_file(request: Request):
    """Upload audio file for processing"""
    try:
        logger.info("Received upload request")
        
        # Parse multipart form data
        async with request.form() as form:
            file = form.get('file')
            
            if not file or not hasattr(file, 'filename'):
                logger.error("No file in request")
                raise HTTPException(status_code=400, detail="No file provided")
            
            filename = file.filename
            if not filename:
                logger.error("Empty filename")
                raise HTTPException(status_code=400, detail="Empty filename")
            
            logger.info(f"Processing file: {filename}")
            
            if not filename.lower().endswith((".wav", ".flac", ".aiff")):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid format. Supported: WAV, FLAC, AIFF",
                )

            # Generate unique session ID
            session_id = str(uuid.uuid4())
            session_dir = UPLOAD_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Save file
            file_path = session_dir / filename
            logger.info(f"Saving to: {file_path}")
            
            # Read and save file content
            content = await file.read()
            logger.info(f"Read {len(content)} bytes")
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Verify file was saved
            if not file_path.exists():
                raise HTTPException(status_code=500, detail="Failed to save file")
            
            file_size_mb = len(content) / 1024 / 1024
            logger.info(f"Uploaded: {filename} ({file_size_mb:.1f} MB)")

            active_sessions[session_id] = {
                "file_path": file_path,
                "filename": filename,
                "size_mb": file_size_mb,
            }

            return {
                "session_id": session_id,
                "filename": filename,
                "size_mb": round(file_size_mb, 1),
                "status": "ready",
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/configure")
async def configure_pipeline(config: PipelineConfig):
    """Configure pipeline parameters"""
    pipeline.configure(config.dict())
    logger.info(f"Pipeline configured: {config.dict()}")
    return {"status": "configured", "config": config.dict()}


@app.post("/api/studio-config")
async def configure_studio(config: StudioConfig):
    """Configure studio tuning parameters"""
    pipeline.set_studio_config(config.dict())
    logger.info(f"Studio config: {config.dict()}")
    return {"status": "configured", "config": config.dict()}


@app.post("/api/studio-preset/{preset_name}")
async def apply_studio_preset(preset_name: str):
    """Apply studio tuning preset"""
    if preset_name not in STUDIO_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {preset_name}")

    preset = STUDIO_PRESETS[preset_name]
    pipeline.set_studio_config(preset)
    logger.info(f"Studio preset applied: {preset_name}")
    return {"status": "applied", "preset": preset_name, "config": preset}


@app.post("/api/run")
async def run_pipeline(background_tasks: BackgroundTasks):
    """Start the pipeline processing"""
    if pipeline.is_running:
        raise HTTPException(status_code=400, detail="Pipeline already running")

    # Get latest session
    if not active_sessions:
        raise HTTPException(status_code=400, detail="No file uploaded")

    session_id = list(active_sessions.keys())[-1]
    session = active_sessions[session_id]

    input_path = session["file_path"]
    output_dir = OUTPUT_DIR / session_id

    logger.info(f"Starting pipeline for session: {session_id}")

    # Run pipeline in background
    async def run():
        result = await pipeline.run(input_path, output_dir)
        session["result"] = result

    background_tasks.add_task(run)

    return {
        "status": "started",
        "session_id": session_id,
        "message": "Pipeline started",
    }


@app.get("/api/export/{session_id}")
async def get_export_files(session_id: str):
    """Get list of exported files for a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]
    result = session.get("result", {})

    if result.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Pipeline not complete")

    exported_files = result.get("exported_files", [])
    return {"files": exported_files}


@app.get("/api/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """Download an exported file"""
    file_path = OUTPUT_DIR / session_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@app.get("/api/presets")
async def get_presets():
    """Get available studio presets"""
    return {"presets": STUDIO_PRESETS}


# Mount static files
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")


# ============ Startup ============


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting 5.1 AutoMaster server...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")

    uvicorn.run(app, host="127.0.0.1", port=8000)
