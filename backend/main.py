import logging
import os
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from api.auth import router as auth_router
from db.database import engine, Base
from db import models  # noqa: F401 - registers models on Base before create_all

Base.metadata.create_all(bind=engine)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Industrial Mind OS API",
    description="Backend services for the Industrial Mind OS distributed knowledge framework",
    version="1.0.0"
)

# CORS Configuration - Allow Frontend Origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core API routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint to verify the API is serving requests."""
    return {"message": "Welcome to the Industrial Mind OS API. Visit /docs for documentation."}

@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify backend is running."""
    return {"status": "ok", "service": "industrial-mind-os-core"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
