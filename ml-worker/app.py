from fastapi import FastAPI, HTTPException

app = FastAPI(title="Oratoria ML Worker", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/process")
async def process_video():
    raise HTTPException(status_code=501, detail="Not implemented yet")
