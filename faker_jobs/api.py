"""
FastAPI REST API for Faker Jobs Provider.

Provides endpoints to generate job postings, candidates, CVs, and datasets
via HTTP requests.

Usage:
    python -m faker_jobs.api  # Starts the server on http://localhost:8000
    
    # Or programmatically:
    from faker_jobs.api import app
    # Use with uvicorn: uvicorn faker_jobs.api:app --reload

Endpoints:
    GET  /postings           - List job postings
    GET  /postings/{id}      - Get a specific posting
    GET  /companies          - List companies
    GET  /candidates          - List candidates
    GET  /candidates/{id}/cv - Get CV for a candidate
    POST /datasets           - Generate a dataset
    GET  /locales            - List available locales
    GET  /sectors            - List activity sectors
    GET  /occupations        - List occupations
"""
from __future__ import annotations

import datetime as _datetime
import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from faker import Faker

from faker_jobs import JobsProvider


# Initialize FastAPI app
app = FastAPI(
    title="Faker Jobs API",
    description="Generate realistic fake job market data via REST API",
    version="0.13.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models for request/response
class PostingParams(BaseModel):
    """Parameters for generating postings."""
    locale: str = "en_US"
    count: int = 1
    code: str | None = None
    sector: str | None = None
    country: str | None = None
    weighted: bool = True


class DatasetParams(BaseModel):
    """Parameters for generating datasets."""
    locale: str = "en_US"
    postings: int = 1000
    companies: int | None = None
    start_date: str = "-2y"
    end_date: str = "today"
    repost_rate: float = 0.08
    id_template: str | None = None
    dirty: float = 0.0
    candidates: int = 0
    applications: float = 10.0


class CVParams(BaseModel):
    """Parameters for generating CVs."""
    locale: str = "en_US"
    code: str | None = None
    sector: str | None = None
    output_format: str = "dict"  # dict, json, markdown


class CompanyParams(BaseModel):
    """Parameters for generating companies."""
    locale: str = "en_US"
    count: int = 1
    sector: str | None = None


class CandidateParams(BaseModel):
    """Parameters for generating candidates."""
    locale: str = "en_US"
    count: int = 1
    code: str | None = None
    sector: str | None = None
    weighted: bool = True


# Helper to get a JobsProvider for a locale
def _get_provider(locale: str) -> JobsProvider:
    """Get or create a JobsProvider for a given locale."""
    # Use a module-level cache
    if not hasattr(_get_provider, "_providers"):
        _get_provider._providers: dict[str, JobsProvider] = {}
    
    if locale not in _get_provider._providers:
        fake = Faker(locale)
        _get_provider._providers[locale] = JobsProvider(fake)
    
    return _get_provider._providers[locale]


# Cache for generated data
_DATA_CACHE: dict[str, Any] = {}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Faker Jobs API",
        "version": "0.13.0",
        "docs": "/docs",
        "endpoints": {
            "GET /postings": "Generate job postings",
            "GET /postings/{id}": "Get a specific posting",
            "GET /companies": "Generate companies",
            "GET /candidates": "Generate candidates",
            "GET /candidates/{id}/cv": "Get CV for a candidate",
            "POST /datasets": "Generate a dataset",
            "GET /locales": "List available locales",
            "GET /sectors": "List activity sectors",
            "GET /occupations": "List occupations",
        }
    }


# ==================== Postings Endpoints ====================

@app.get("/postings")
async def get_postings(
    locale: str = Query(default="en_US", description="Faker locale (e.g., fr_FR, de_DE, en_US)"),
    count: int = Query(default=1, ge=1, le=100, description="Number of postings to generate"),
    code: str | None = Query(default=None, description="Occupation code to filter by"),
    sector: str | None = Query(default=None, description="Activity sector to filter by"),
    country: str | None = Query(default=None, description="Country to filter by"),
    weighted: bool = Query(default=True, description="Pick occupations by demand"),
):
    """Generate one or more job postings."""
    try:
        provider = _get_provider(locale)
        postings = []
        
        for _ in range(count):
            posting = provider.job_posting(
                code=code,
                sector=sector,
                country=country,
                weighted=weighted,
            )
            # Convert datetime to string for JSON serialization
            if isinstance(posting.get("job_posting_date"), _datetime.date):
                posting["job_posting_date"] = posting["job_posting_date"].isoformat()
            postings.append(posting)
        
        return JSONResponse(content=postings if count > 1 else postings[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/postings/{posting_id}")
async def get_posting(
    posting_id: str,
    locale: str = Query(default="en_US", description="Faker locale"),
):
    """Get a specific job posting by ID."""
    try:
        # For now, just generate a new posting (in a real scenario, we'd cache or use the ID)
        provider = _get_provider(locale)
        posting = provider.job_posting()
        
        if isinstance(posting.get("job_posting_date"), _datetime.date):
            posting["job_posting_date"] = posting["job_posting_date"].isoformat()
        
        return JSONResponse(content=posting)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Posting not found: {e}")


# ==================== Companies Endpoints ====================

@app.get("/companies")
async def get_companies(
    locale: str = Query(default="en_US", description="Faker locale"),
    count: int = Query(default=1, ge=1, le=100, description="Number of companies to generate"),
    sector: str | None = Query(default=None, description="Activity sector to filter by"),
):
    """Generate one or more company profiles."""
    try:
        provider = _get_provider(locale)
        companies = []
        
        for _ in range(count):
            company = provider.job_company_profile(sector=sector)
            companies.append(company)
        
        return JSONResponse(content=companies if count > 1 else companies[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Candidates Endpoints ====================

@app.get("/candidates")
async def get_candidates(
    locale: str = Query(default="en_US", description="Faker locale"),
    count: int = Query(default=1, ge=1, le=100, description="Number of candidates to generate"),
    code: str | None = Query(default=None, description="Occupation code to filter by"),
    sector: str | None = Query(default=None, description="Activity sector to filter by"),
    weighted: bool = Query(default=True, description="Pick occupations by demand"),
):
    """Generate one or more job candidates."""
    try:
        provider = _get_provider(locale)
        candidates = []
        
        for _ in range(count):
            candidate = provider.job_candidate(
                code=code,
                sector=sector,
                weighted=weighted,
            )
            candidates.append(candidate)
        
        return JSONResponse(content=candidates if count > 1 else candidates[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/candidates/{candidate_id}/cv")
async def get_candidate_cv(
    candidate_id: str,
    locale: str = Query(default="en_US", description="Faker locale"),
    output_format: str = Query(default="dict", description="Output format: dict, json, markdown"),
):
    """Get a CV for a specific candidate."""
    try:
        provider = _get_provider(locale)
        
        # Generate a candidate (in a real scenario, we'd use the candidate_id)
        candidate = provider.job_candidate()
        
        cv = provider.job_cv(
            candidate=candidate,
            output_format=output_format,
        )
        
        if output_format == "markdown":
            return JSONResponse(content={"cv": cv["markdown"], "locale": cv.get("locale")})
        
        return JSONResponse(content=cv)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== CV Endpoint ====================

@app.get("/cv")
async def generate_cv(
    locale: str = Query(default="en_US", description="Faker locale"),
    code: str | None = Query(default=None, description="Occupation code"),
    sector: str | None = Query(default=None, description="Activity sector"),
    output_format: str = Query(default="dict", description="Output format: dict, json, markdown"),
):
    """Generate a random CV."""
    try:
        provider = _get_provider(locale)
        cv = provider.job_cv(
            code=code,
            sector=sector,
            output_format=output_format,
        )
        
        if output_format == "markdown":
            return JSONResponse(content={"cv": cv["markdown"], "locale": cv.get("locale")})
        
        return JSONResponse(content=cv)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Dataset Endpoint ====================

@app.post("/datasets")
async def create_dataset(
    params: DatasetParams,
):
    """Generate a dataset of job postings, companies, and optionally candidates."""
    try:
        provider = _get_provider(params.locale)
        
        dataset = provider.job_dataset(
            postings=params.postings,
            companies=params.companies,
            start_date=params.start_date,
            end_date=params.end_date,
            repost_rate=params.repost_rate,
            id_template=params.id_template,
            dirty=params.dirty,
            candidates=params.candidates,
            applications=params.applications,
        )
        
        # Convert to serializable format
        result = {
            "companies": dataset.companies,
            "postings": dataset.postings,
        }
        
        if dataset.candidates:
            result["candidates"] = dataset.candidates
        if dataset.applications:
            result["applications"] = dataset.applications
        if dataset.defects:
            result["defects"] = dataset.defects
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Metadata Endpoints ====================

@app.get("/locales")
async def get_locales():
    """List available locales."""
    # Get all available locales from Faker
    return {
        "available_locales": list(Faker().locales),
        "recommended": [
            "en_US", "fr_FR", "de_DE", "es_ES", "it_IT",
            "pt_PT", "pt_BR", "nl_NL", "pl_PL", "sv_SE",
            "cs_CZ", "ro_RO", "el_GR", "ar_SA"
        ],
        "note": "All Faker locales are supported. The recommended ones have full occupation data."
    }


@app.get("/sectors")
async def get_sectors(
    locale: str = Query(default="en_US", description="Faker locale"),
):
    """List activity sectors for a locale."""
    try:
        provider = _get_provider(locale)
        sectors = provider.job_activity_sectors
        return {"locale": locale, "sectors": sectors}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/occupations")
async def get_occupations(
    locale: str = Query(default="en_US", description="Faker locale"),
    sector: str | None = Query(default=None, description="Filter by sector"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of occupations to return"),
):
    """List occupations for a locale, optionally filtered by sector."""
    try:
        provider = _get_provider(locale)
        codes = provider.job_occupation_codes
        
        occupations = []
        for code in codes[:limit]:
            try:
                occ = provider.job_occupation_record(code=code)
                if sector is None or sector in occ.get("sectors", []):
                    occupations.append({
                        "code": occ["code"],
                        "title": occ["title"],
                        "sector": occ.get("sector"),
                        "sectors": occ.get("sectors", []),
                        "isco_code": occ.get("isco_code"),
                        "isco_group": occ.get("isco_group"),
                        "demand": occ.get("demand", 0),
                    })
            except Exception:
                continue
        
        return {"locale": locale, "occupations": occupations, "total": len(codes)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/countries")
async def get_countries():
    """List available countries."""
    try:
        provider = _get_provider("en_US")
        countries = provider.job_countries
        return {"countries": countries, "count": len(countries)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.13.0",
        "timestamp": _datetime.datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
