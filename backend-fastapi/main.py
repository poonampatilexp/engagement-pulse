import os
import sys

# Ensure backend-fastapi directory is in Python path for standalone executions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.auth import router as auth_router
from routers.organisations import router as organisations_router
from routers.projects import router as projects_router
from routers.risks import router as risks_router
from routers.csv_jobs import router as csv_jobs_router

app = FastAPI(
    title="Engagement Pulse API",
    description="FastAPI backend for Engagement Pulse engagement risk management",
    version="0.1.0",
)

# Configure CORS for local Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints with and without /api prefix for compatibility
app.include_router(auth_router)
app.include_router(organisations_router)
app.include_router(projects_router)
app.include_router(risks_router)
app.include_router(csv_jobs_router)

app.include_router(auth_router, prefix="/api")
app.include_router(organisations_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(risks_router, prefix="/api")
app.include_router(csv_jobs_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
