import os
from dotenv import load_dotenv
load_dotenv()

import logging
import json
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api import auth, frontend, whatsapp
from src.scheduler import init_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Override uvicorn loggers to use the same format
for uvicorn_logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    for handler in uvicorn_logger.handlers:
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))

app = FastAPI(title="Help U - Bookkeeper Backend")

# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Logs validation errors for debugging"""
    logger.error(f"Validation error for {request.method} {request.url}: {exc.errors()}")
    return Response(status_code=422, content=json.dumps({"detail": exc.errors()}), media_type="application/json")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        whatsapp_id = request.query_params.get('whatsapp_id') or "No ID"
        logger.warning(f"401 Unauthorized for {request.url.path} | User: {whatsapp_id} | Detail: {exc.detail}")
    return Response(status_code=exc.status_code, content=json.dumps({"detail": exc.detail}), media_type="application/json")

# Startup Event
@app.on_event("startup")
async def startup_event():
    """Initializes background tasks on server start"""
    # Ensure temporary media directory exists
    if not os.path.exists("temp_media"):
        os.makedirs("temp_media")
        logger.info("Created temp_media directory")
        
    init_scheduler()
    logger.info("Application startup complete.")

# Include Routers
app.include_router(auth.router)
app.include_router(frontend.router)
app.include_router(whatsapp.router)

# Serve Static Files (Frontend)
frontend_path = os.path.join("src", "frontend", "dist")
if os.path.exists(frontend_path):
    # Vite/React assets folder
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    # Root static files (vite.svg, etc)
    @app.get("/{file_name}")
    async def serve_root_file(file_name: str):
        file_path = os.path.join(frontend_path, file_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to SPA routing logic
        return await serve_frontend(file_name)

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serves the React frontend for any non-API route"""
        # Exclude API routes, static files, and verification token
        if full_path.startswith("api/") or full_path.startswith("auth/") or full_path == "webhook" or full_path.startswith("assets/"):
            raise HTTPException(status_code=404)
        
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
