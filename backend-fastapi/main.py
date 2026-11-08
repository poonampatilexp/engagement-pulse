import os
import sys

# Ensure backend-fastapi directory is in Python path for standalone executions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.organisations import router as organisations_router
from routers.projects import router as projects_router

app = FastAPI(
    title="Engagement Pulse API",
    description="FastAPI backend for Engagement Pulse engagement risk management",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(organisations_router)
app.include_router(projects_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
