#!/usr/bin/env python3
"""
Simple FastAPI server for coding platform only - no ML dependencies
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app
app = FastAPI(title="Coding Platform API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import only coding API
from app.api.coding import router as coding_router

# Add routes
app.include_router(coding_router, prefix="/api/coding", tags=["coding"])

@app.get("/")
def root():
    return {"message": "Coding Platform API is running!", "docs": "/docs"}

if __name__ == "__main__":
    print("Starting Coding Platform API on http://127.0.0.1:8000 ...")
    print("API Documentation available at: http://127.0.0.1:8000/docs")
    uvicorn.run("run_coding_only:app", host="127.0.0.1", port=8000, reload=True)