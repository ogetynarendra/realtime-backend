from future import annotations

import os
from typing import List, Optional, Dict, Any

import requests
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
title="AI Co‑Pilot Real‑Time Backend",
description="Provides real‑time company data via various APIs",
version="0.1.1",
)

def search_google_places(query: str, location: Optional[str] = None, *, n_results: int = 5) -> List[Dict[str, Any]]:
"""Search for businesses using the Google Places Text Search API.

pgsql
Copy
This helper wraps the Google Maps Text Search endpoint and returns a
simplified list of results.  You must provide a valid API key via the
`GOOGLE_MAPS_API_KEY` environment variable.  If the key is missing or the
request fails, an HTTPException will be raised.

Parameters
----------
query: str
    A search query describing the business or industry (e.g. "plumbing companies").
location: Optional[str]
    Optional location to bias results (e.g. "Chicago, IL").  If provided,
    it will be appended to the search string as "<query> in <location>".
n_results: int, optional
    Maximum number of results to return (default is 5).

Returns
-------
list[dict[str, Any]]
    A list of dictionaries containing the business name, formatted address,
    categories and a link back to Google Maps.  Missing fields are
    represented as ``None``.
"""
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
if not api_key:
    raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY is not set")

# Build the search query; include location if provided and non‑empty
search_text = query.strip()
if location:
    search_text = f"{search_text} in {location.strip()}"

url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
params = {
    "query": search_text,
    "key": api_key,
}

try:
    resp = requests.get(url, params=params, timeout=10)
except requests.RequestException as exc:
    raise HTTPException(status_code=503, detail=f"Failed to contact Google Places API: {exc}")

if resp.status_code != 200:
    raise HTTPException(
        status_code=resp.status_code,
        detail=f"Google Places API returned {resp.status_code}: {resp.text}",
    )

data = resp.json()
results: List[Dict[str, Any]] = []
for item in data.get("results", [])[:n_results]:
    results.append({
        "name": item.get("name"),
        "business_type": ", ".join(item.get("types", [])) if item.get("types") else None,
        "location": item.get("formatted_address"),
        "address": item.get("formatted_address"),
        "revenue": None,  # Revenue is not available via the Places API
        "contact": None,
        "source_url": f"https://maps.google.com/?cid={item.get('place_id')}" if item.get("place_id") else None,
    })
return results
def search_crunchbase(query: str) -> List[Dict[str, Any]]:
"""Placeholder for a Crunchbase search.
Crunchbase offers a free tier that exposes limited company data via its API
when you register for a developer account.  To implement this function you
need to obtain an API key and call the Crunchbase REST endpoints.  See
https://data.crunchbase.com/docs/api-overview for details.
"""
# TODO: implement using the Crunchbase API
return []

def search_sbic_directory(industry: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
"""Placeholder for the Small Business Investment Company (SBIC) directory.

pgsql
Copy
The SBA provides a CSV directory of SBIC licensees.  You can download the
CSV from sba.gov and parse it with pandas to filter by industry keywords
and state codes.  Each record should include at least the firm name,
address and contact information when available.
"""
# TODO: implement CSV parsing and filtering
return []
def search_sec_adv(industry: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
"""Placeholder for SEC Form ADV data extraction.

pgsql
Copy
@app.get(
"/companies",
summary="Search for companies",
response_description="List of companies",
)
def get_companies(
industry: str = Query(..., description="Industry keyword, e.g. 'plumbing', 'landscaping'"),
city: Optional[str] = Query(None, description="City for location bias, e.g. 'Chicago'"),
state: Optional[str] = Query(None, description="State code or full name, e.g. 'IL' or 'Illinois'"),
limit: int = Query(10, ge=1, le=50, description="Maximum number of records to return"),
include_sources: bool = Query(True, alias="include_sources", description="Include source URLs in the response"),
) -> List[Dict[str, Any]]:
"""Aggregate company data from multiple sources.
This endpoint orchestrates calls to various search functions.  It first
queries Google Places for quick discovery of businesses in the given
industry and location.  It then queries other registries (Crunchbase,
SBIC, SEC) to enrich or supplement the results.  Duplicate entries are
collapsed and enriched with available fields.
"""
aggregated: Dict[str, Dict[str, Any]] = {}

# Build a clean location string; avoid trailing commas when only one field is provided
location_parts: List[str] = []
if city:
    location_parts.append(city)
if state:
    location_parts.append(state)
location: Optional[str] = ", ".join(location_parts) if location_parts else None

# Google Places search; wrap in try/except so we don't abort the entire request on failure
try:
    g_results = search_google_places(f"{industry} companies", location, n_results=limit)
except HTTPException:
    g_results = []

for res in g_results:
    name = res.get("name")
    if name:
        aggregated[name] = res

# Crunchbase (placeholder)
cb_results = search_crunchbase(industry)
for res in cb_results:
    name = res.get("name")
    if not name:
        continue
    existing = aggregated.get(name, {})
    for key, val in res.items():
        if val and not existing.get(key):
            existing[key] = val
    aggregated[name] = existing

# SBIC directory (placeholder)
sbic_results = search_sbic_directory(industry, state)
for res in sbic_results:
    name = res.get("name")
    if not name:
        continue
    existing = aggregated.get(name, {})
    for key, val in res.items():
        if val and not existing.get(key):
            existing[key] = val
    aggregated[name] = existing

# SEC Form ADV (placeholder)
sec_results = search_sec_adv(industry, state)
for res in sec_results:
    name = res.get("name")
    if not name:
        continue
    existing = aggregated.get(name, {})
    for key, val in res.items():
        if val and not existing.get(key):
            existing[key] = val
    aggregated[name] = existing

# Convert aggregated dict to a list and cap to limit
items = list(aggregated.values())[:limit]

# Remove source URL if requested
if not include_sources:
    for item in items:
        item.pop("source_url", None)

return items
@app.get("/healthz", summary="Health check")
def health_check() -> Dict[str, str]:
"""Simple health check endpoint."""
return {"status": "ok"}
