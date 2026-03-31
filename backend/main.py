"""
5.1 AutoMaster - FastAPI Server
Main entry point for localhost deployment
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
import json

# Optional imports (fail gracefully if not available)
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from config.constants import OUTPUT_DIR, TEMP_DIR, UPLOAD_DIR, STUDIO_PRESETS
from core.pipeline import PipelineManager

# Global output directory (can be changed via API)
CURRENT_OUTPUT_DIR = OUTPUT_DIR

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

# No-cache middleware — ensures JS/CSS/HTML are always fresh after server restart
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    # Apply no-cache to all frontend assets
    if path.startswith('/js/') or path.startswith('/css/') or path == '/':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Global pipeline instance
pipeline = PipelineManager()
active_sessions: Dict[str, Dict] = {}
active_pipeline_task: Optional[asyncio.Task] = None

# Persistent session storage
SESSIONS_FILE = Path("sessions.json")

def load_sessions():
    """Load sessions from disk on startup"""
    global active_sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                active_sessions = json.load(f)
            logger.info(f"Loaded {len(active_sessions)} sessions from {SESSIONS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            active_sessions = {}
    else:
        logger.info("No existing sessions found")

def save_sessions():
    """Save sessions to disk"""
    try:
        # Convert Path objects to strings for JSON serialization
        serializable_sessions = {}
        for session_id, session in active_sessions.items():
            serializable_session = session.copy()
            if 'file_path' in serializable_session:
                serializable_session['file_path'] = str(serializable_session['file_path'])
            if 'result' in serializable_session and 'output_dir' in serializable_session.get('result', {}):
                serializable_session['result']['output_dir'] = str(serializable_session['result']['output_dir'])
            serializable_sessions[session_id] = serializable_session
        
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_sessions, f, indent=2)
        logger.debug(f"Saved {len(active_sessions)} sessions to {SESSIONS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")


# ============ Models ============


class PipelineConfig(BaseModel):
    target_lufs: float = -14.0  # Spotify streaming target
    stem_model: str = "htdemucs_6s"
    silence_gate: int = -50
    output_format: str = "wav_48k_24bit"
    studio_preset: str = "pop"
    mode: str = "basic"  # "basic" or "pro"
    cut_points: List[float] = []
    skip_track_cutting: bool = True  # Off by default for Suno tracks


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
    exported_files: Optional[List[Dict]] = []


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
                "file_path": str(file_path),
                "filename": filename,
                "size_mb": file_size_mb,
            }
            
            # Persist session to disk
            save_sessions()

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
async def run_pipeline():
    """Start the pipeline processing"""
    global active_pipeline_task
    
    if pipeline.is_running:
        raise HTTPException(status_code=400, detail="Pipeline already running")

    # Get latest session
    if not active_sessions:
        raise HTTPException(status_code=400, detail="No file uploaded")

    session_id = list(active_sessions.keys())[-1]
    session = active_sessions[session_id]

    input_path = Path(session["file_path"])
    output_dir = OUTPUT_DIR / session_id

    # Make original filename available for dynamic export names
    pipeline.context["original_filename"] = session["filename"]

    logger.info(f"Starting pipeline for session: {session_id}")

    # Run pipeline as an explicit task that can be cancelled
    async def run():
        try:
            result = await pipeline.run(input_path, output_dir)
            session["result"] = result
            if 'output_dir' in result:
                result['output_dir'] = str(result['output_dir'])
            save_sessions()
            logger.info(f"Pipeline complete for session {session_id}")
        except asyncio.CancelledError:
            logger.info(f"Pipeline task was cancelled for session {session_id}")
            # Ensure pipeline state is reset
            pipeline.is_running = False
            session["result"] = {"status": "aborted", "error": "Processing was aborted by user"}
            save_sessions()
        except Exception as e:
            logger.error(f"Pipeline failed for session {session_id}: {e}")
            session["result"] = {"status": "error", "error": str(e)}
            save_sessions()

    active_pipeline_task = asyncio.create_task(run())

    return {
        "status": "started",
        "session_id": session_id,
        "message": "Pipeline started",
    }


@app.post("/api/abort")
async def abort_pipeline():
    """Abort the currently running pipeline"""
    global active_pipeline_task
    
    if not pipeline.is_running:
        return {"status": "not_running", "message": "No pipeline is currently running"}
    
    logger.info("Abort request received via API")
    
    # 1. Signal the pipeline manager (for clean breaks between stages)
    pipeline.abort()
    
    # 2. Cancel the background task (to interrupt async blocks)
    if active_pipeline_task and not active_pipeline_task.done():
        active_pipeline_task.cancel()
        logger.info("Active pipeline task cancelled")
    
    return {"status": "aborted", "message": "Pipeline is being aborted"}


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
    from urllib.parse import unquote

    # Decode URL-encoded filename (in case it was encoded by the frontend)
    filename = unquote(filename)

    file_path = CURRENT_OUTPUT_DIR / session_id / filename

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    from urllib.parse import quote

    response = FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )
    # Explicitly set Content-Disposition for non-ASCII filenames
    content_disposition = f'attachment; filename="{filename}"; filename*=utf-8\'\'{quote(filename)}'
    response.headers["Content-Disposition"] = content_disposition
    response.headers["Content-Length"] = str(file_path.stat().st_size)
    return response


@app.get("/api/download-archive/{session_id}")
async def download_archive(session_id: str):
    """Zip all exported files for a session and return as a download"""
    try:
        import zipfile
        session = active_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        exported_files = session.get("result", {}).get("exported_files", [])
        if not exported_files:
            raise HTTPException(status_code=404, detail="No exported files found")

        # Build zip next to output files (avoids temp dir permission issues)
        output_dir = CURRENT_OUTPUT_DIR / session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get original filename without extension for zip name
        original_filename = session.get("filename", f"AutoMaster_{session_id[:8]}")
        base_name = Path(original_filename).stem
        zip_name = f"{base_name}_Master.zip"
        zip_path = output_dir / zip_name

        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in exported_files:
                fp = Path(f["path"])
                if fp.exists():
                    zf.write(str(fp), fp.name)
                    logger.info(f"Added to zip: {fp.name}")

        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Failed to create archive")

        logger.info(f"Archive ready: {zip_path} ({zip_path.stat().st_size} bytes)")
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=zip_path.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Archive error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CutPointsRequest(BaseModel):
    cut_points: List[float] = []


class OutputDirRequest(BaseModel):
    path: str


@app.post("/api/cut-points")
async def save_cut_points(data: CutPointsRequest):
    """Save manual cut points for the current session"""
    if not active_sessions:
        raise HTTPException(status_code=400, detail="No active session")

    session_id = list(active_sessions.keys())[-1]
    active_sessions[session_id]["cut_points"] = data.cut_points

    logger.info(f"Saved {len(data.cut_points)} cut points for session {session_id}")
    return {"status": "saved", "cut_points": data.cut_points}


@app.get("/api/cut-points")
async def get_cut_points():
    """Get saved cut points for the current session"""
    if not active_sessions:
        return {"cut_points": []}

    session_id = list(active_sessions.keys())[-1]
    cut_points = active_sessions.get(session_id, {}).get("cut_points", [])

    return {"cut_points": cut_points}


@app.get("/api/output-dir")
async def get_output_dir():
    """Get current output directory"""
    return {"path": str(CURRENT_OUTPUT_DIR), "default": str(OUTPUT_DIR)}


@app.post("/api/output-dir")
async def set_output_dir(data: OutputDirRequest):
    """Set output directory for downloads"""
    global CURRENT_OUTPUT_DIR
    
    new_path = Path(data.path)
    
    # Validate path
    if not new_path.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")
    
    # Create directory if it doesn't exist
    try:
        new_path.mkdir(parents=True, exist_ok=True)
        CURRENT_OUTPUT_DIR = new_path
        logger.info(f"Output directory changed to: {new_path}")
        return {"status": "success", "path": str(new_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot create directory: {e}")


@app.get("/api/presets")
async def get_presets():
    """Get available studio presets"""
    return {"presets": STUDIO_PRESETS}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its files"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    # Delete output files
    output_dir = CURRENT_OUTPUT_DIR / session_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
        logger.info(f"Deleted output directory: {output_dir}")
    
    # Delete upload files
    file_path = Path(session.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
        logger.info(f"Deleted upload file: {file_path}")
    
    # Remove from sessions
    del active_sessions[session_id]
    save_sessions()
    
    return {"status": "deleted", "session_id": session_id}


@app.get("/api/sessions")
async def list_sessions():
    """List all stored sessions"""
    sessions = []
    for session_id, session in active_sessions.items():
        sessions.append({
            "session_id": session_id,
            "filename": session.get("filename", "unknown"),
            "size_mb": session.get("size_mb", 0),
            "status": "complete" if session.get("result", {}).get("status") == "complete" else "pending",
            "exported_files": session.get("result", {}).get("exported_files", []),
        })
    return {"sessions": sessions}


@app.post("/api/shutdown")
async def shutdown():
    """Gracefully shut down the server"""
    import os, signal
    logger.info("Shutdown requested via API")

    async def _stop():
        await asyncio.sleep(0.2)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_stop())
    return {"status": "shutting_down"}


# Mount static files
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")


# Debug page for testing
@app.get("/debug.html")
async def get_debug_page():
    """Serve debug console for testing"""
    from fastapi.responses import FileResponse
    return FileResponse("frontend/debug.html")


# ============ Startup ============


@app.on_event("startup")
async def startup_event():
    """Load persistent sessions on server startup"""
    load_sessions()
    logger.info(f"Output directory: {CURRENT_OUTPUT_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")
    logger.info(f"Upload directory: {UPLOAD_DIR}")


def find_free_port(start: int = 8000) -> int:
    """Find the first available TCP port starting from `start`."""
    import socket
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range 8000–8099")


if __name__ == "__main__":
    import uvicorn
    import threading
    import webbrowser

    port = find_free_port()

    # Write port to file so restart.bat can open the browser on the right URL
    Path(".port").write_text(str(port))

    logger.info(f"Starting 5.1 AutoMaster server on port {port}...")
    logger.info(f"Output directory: {CURRENT_OUTPUT_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")

    # Open browser automatically once the server is ready
    def _open_browser():
        import time, subprocess
        time.sleep(1.5)  # Give uvicorn time to bind the port
        url = f"http://127.0.0.1:{port}"
        try:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        except Exception:
            webbrowser.open(url)  # fallback

    threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port)
