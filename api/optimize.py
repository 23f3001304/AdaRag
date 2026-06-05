"""Optimizer endpoint: kick off a bucket-tuning Optuna study and poll its live progress."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["optimize"])


class StudyRequest(BaseModel):
    bucket: str = "default"
    trials: int = 20
    max_queries: int = 12


@router.post("/optimize/run")
async def run(request: Request, body: StudyRequest) -> dict:
    """Start a tuning study over a bucket (one at a time); reports whether it started."""
    study = request.app.state.study
    started = study.start(body.bucket, body.trials, body.max_queries)
    return {"started": started, "running": study.running}


@router.get("/optimize/status")
async def status(request: Request) -> dict:
    """The current study's progress and result (or idle)."""
    return request.app.state.study.state
