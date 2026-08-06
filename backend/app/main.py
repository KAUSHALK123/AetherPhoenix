from fastapi import FastAPI

app = FastAPI(
    title="AetherPhoenix Backend",
    version="0.1.0",
    description="Backend foundation for AI Desktop Assistant",
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
