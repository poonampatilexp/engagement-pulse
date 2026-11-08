from fastapi import FastAPI

app = FastAPI(
    title="Engagement Pulse API",
    description="FastAPI backend for Engagement Pulse engagement risk management",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


