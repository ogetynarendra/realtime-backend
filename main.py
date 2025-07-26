from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional, Dict, Any
import os
import requests

app = FastAPI(title="AI Co‑Pilot Real‑Time Backend",
              description="Provides real‑time company data via various APIs",
              version="0.1.0")

def search_google_places(query: str, location: Optional[str] = None, n_results: int = 5) -> List[Dict[str, Any]]:
    """Query the Google Places Text Search API for businesses matching the query.
    If the GOOGLE_MAPS_API_KEY environment variable is missing, returns an empty list.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return []
    search_text = f"{query} in {location}" if location else query
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": search_text, "key": api_key}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json().get("results", [])
    results: List[Dict[str, Any]] = []
    for item in data[:n_results]:
        results.append({
            "name": item.get("name"),
            "business_type": ", ".join(item.get("types", [])) if item.get("types") else None,
            "location": item.get("formatted_address"),
            "address": item.get("formatted_address"),
            "revenue": None,
            "phone": None,
            "email": None,
            "source": f"https://maps.google.com/?cid={item.get('place_id')}"
        })
    return results

def search_crunchbase(query: str) -> List[Dict[str, Any]]:
    """Placeholder for Crunchbase search. Implement your API calls here."""
    return []

def search_sbic_directory(industry: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """Placeholder for SBIC directory search. Implement CSV parsing here."""
    return []

def search_sec_adv(industry: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
    """Placeholder for SEC Form ADV search. Implement data extraction here."""
    return []

@app.get("/companies", summary="Search for companies")
def get_companies(
    industry: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10,
    include_sources: bool = True
) -> List[Dict[str, Any]]:
    """Aggregate company data from multiple sources.

    This endpoint queries Google Places and other sources (placeholders) to build
    a deduplicated list of companies. Set include_sources=False to omit source URLs.
    """
    aggregated: Dict[str, Dict[str, Any]] = {}
    # Google search: combine industry with 'companies' for better results
    search_query = f"{industry} companies"
    location = f"{city or ''} {state or ''}".strip() or None
    g_results = search_google_places(search_query, location, n_results=limit)
    for res in g_results:
        name = res.get("name")
        if name:
            aggregated[name] = res
    # Crunchbase
    for res in search_crunchbase(industry):
        name = res.get("name")
        if name:
            existing = aggregated.get(name, {})
            for k, v in res.items():
                if v and not existing.get(k):
                    existing[k] = v
            aggregated[name] = existing
    # SBIC directory
    for res in search_sbic_directory(industry, state):
        name = res.get("name")
        if name:
            existing = aggregated.get(name, {})
            for k, v in res.items():
                if v and not existing.get(k):
                    existing[k] = v
            aggregated[name] = existing
    # SEC Form ADV
    for res in search_sec_adv(industry, state):
        name = res.get("name")
        if name:
            existing = aggregated.get(name, {})
            for k, v in res.items():
                if v and not existing.get(k):
                    existing[k] = v
            aggregated[name] = existing
    # Limit results
    items = list(aggregated.values())[:limit]
    if not include_sources:
        for item in items:
            item.pop("source", None)
    return items

@app.get("/healthz", summary="Health check")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}
