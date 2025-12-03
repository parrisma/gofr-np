#!/usr/bin/env python3
"""Web server placeholder - minimal FastAPI server."""

from fastapi import FastAPI

app = FastAPI(title="gofr-np-web")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"service": "gofr-np", "status": "running"}
