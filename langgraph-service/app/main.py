"""FastAPI application entry point for the LangGraph Agentic Workflow Service."""

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables from .env before importing routes.
load_dotenv()

from app.api.routes import router

app = FastAPI(title="LangGraph Agentic Workflow Service")

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
