"""
FastAPI Serving Layer for EPC Competitor Intelligence Agent.

Exposes REST API endpoints for querying historical competitor news,
database telemetry, system health, and triggering on-demand digest runs.
"""

from datetime import datetime, timezone
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import TRACKED_COMPANIES, DB_PATH
from tools.database import NewsDatabase
from core.agent import NewsAgent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EPC Competitor Intelligence API",
    description=(
        "Production-ready REST API for autonomous competitive intelligence monitoring "
        "in the EPC energy sector (tracking Technip Energies NV peers: Saipem, Fluor, Bechtel, etc.)."
    ),
    version="2.0.0",
)

# Enable CORS for local dashboards and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared database instance
db = NewsDatabase()


# ── Pydantic Request/Response Models ──────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    timestamp: str = Field(..., examples=["2026-10-07T12:00:00Z"])
    version: str = Field(..., examples=["2.0.0"])
    database_connected: bool = Field(..., examples=[True])


class ArticleResponse(BaseModel):
    id: int = Field(..., examples=[1])
    title: str = Field(..., examples=["Saipem awarded offshore EPCI contract by QatarEnergy"])
    link: str = Field(..., examples=["https://example.com/saipem-contract"])
    source: str | None = Field(default=None, examples=["Offshore Engineer"])
    published: str | None = Field(default=None, examples=["2026-10-07T10:00:00Z"])
    summary: str | None = Field(default=None, examples=["Saipem has received a major contract..."])
    companies: list[str] = Field(default_factory=list, examples=[["Saipem"]])
    importance: float = Field(..., examples=[22.5])
    created_at: str = Field(..., examples=["2026-10-07T11:00:00Z"])


class ArticlesListResponse(BaseModel):
    total: int = Field(..., examples=[150])
    limit: int = Field(..., examples=[50])
    offset: int = Field(..., examples=[0])
    articles: list[ArticleResponse]


class StatsResponse(BaseModel):
    total_articles: int = Field(..., examples=[728])
    total_tracked_companies: int = Field(..., examples=[15])
    tracked_companies: list[str] = Field(default_factory=list)
    company_breakdown: dict[str, int] = Field(default_factory=dict)


class DigestTriggerResponse(BaseModel):
    status: str = Field(..., examples=["started"])
    message: str = Field(..., examples=["Daily digest pipeline triggered successfully."])
    details: dict[str, Any] = Field(default_factory=dict)


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/", tags=["General"])
def root() -> dict[str, str]:
    """Root metadata and documentation link."""
    return {
        "service": "EPC Competitor Intelligence Agent",
        "version": "2.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health_check() -> HealthResponse:
    """System health check and database connectivity verification."""
    is_connected = False
    try:
        total = db.count_articles()
        is_connected = total >= 0
    except Exception as exc:
        logger.error("Health check database query failed: %s", exc)

    return HealthResponse(
        status="healthy" if is_connected else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="2.0.0",
        database_connected=is_connected,
    )


@app.get("/articles", response_model=ArticlesListResponse, tags=["Articles"])
def get_articles(
    limit: int = Query(default=50, ge=1, le=500, description="Number of articles to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    company: str | None = Query(default=None, description="Filter by company name substring"),
    min_importance: float | None = Query(default=None, description="Minimum importance score"),
) -> ArticlesListResponse:
    """Retrieve historical articles with optional company filter and score threshold."""
    try:
        raw_rows = db.get_articles(
            limit=limit,
            offset=offset,
            company=company,
            min_importance=min_importance,
        )
        total_count = db.count_articles(company=company)

        articles = []
        for r in raw_rows:
            companies_raw = r.get("companies", "") or ""
            companies_list = [c.strip() for c in companies_raw.split(",") if c.strip()]
            articles.append(
                ArticleResponse(
                    id=r["id"],
                    title=r["title"],
                    link=r["link"],
                    source=r.get("source"),
                    published=r.get("published"),
                    summary=r.get("summary"),
                    companies=companies_list,
                    importance=float(r.get("importance", 0.0)),
                    created_at=r.get("created_at", ""),
                )
            )

        return ArticlesListResponse(
            total=total_count,
            limit=limit,
            offset=offset,
            articles=articles,
        )
    except Exception as exc:
        logger.error("Failed to query articles: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}")


@app.get("/stats", response_model=StatsResponse, tags=["Telemetry"])
def get_stats() -> StatsResponse:
    """Retrieve overall monitoring statistics and per-company article distribution."""
    try:
        total = db.count_articles()
        breakdown: dict[str, int] = {}
        for comp in TRACKED_COMPANIES:
            breakdown[comp] = db.count_articles(company=comp)

        return StatsResponse(
            total_articles=total,
            total_tracked_companies=len(TRACKED_COMPANIES),
            tracked_companies=TRACKED_COMPANIES,
            company_breakdown=breakdown,
        )
    except Exception as exc:
        logger.error("Failed to compile stats: %s", exc)
        raise HTTPException(status_code=500, detail=f"Stats calculation error: {exc}")


@app.post("/digest/run", response_model=DigestTriggerResponse, tags=["Pipeline"])
def trigger_digest(background_tasks: BackgroundTasks, async_mode: bool = Query(default=True)) -> DigestTriggerResponse:
    """
    Trigger the daily competitor monitoring pipeline on demand.
    Runs asynchronously in the background by default.
    """
    try:
        agent = NewsAgent()
        if async_mode:
            background_tasks.add_task(agent.run_daily_digest)
            return DigestTriggerResponse(
                status="queued",
                message="Pipeline execution queued in background task.",
                details={"async_mode": True},
            )
        else:
            result = agent.run_daily_digest()
            return DigestTriggerResponse(
                status="completed",
                message="Pipeline execution finished.",
                details=result,
            )
    except Exception as exc:
        logger.error("Digest trigger failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to run pipeline: {exc}")
