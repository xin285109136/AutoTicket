from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from app.models import Offer
from app.skills.search_offers import search_offers
from app.skills.normalize_offers import normalize_offers
from app.core.ranking import rank_offers
from app.core.ai import explain_choice
from app.core.cache import cache
from app.config import settings
from pydantic import BaseModel
import hashlib
import json
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Air Ticket Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Explicit origins + wildcards
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    origin: str
    destination: str
    date: str
    adults: int = 1
    searchMode: str = "scraper"  # 'scraper' or 'api'

def generate_cache_key(req: SearchRequest) -> str:
    return hashlib.md5(f"{req.origin}-{req.destination}-{req.date}-{req.adults}".encode()).hexdigest()

@app.post("/search")
async def search_flights(request: SearchRequest):
    import time
    start_time = time.time()
    
    logger.info(f"Search request: {request.origin}->{request.destination}, mode={request.searchMode}")
    
    # Generate cache key (used for both lookup and storage)
    cache_key = generate_cache_key(request)
    
    # 1. Check Cache (skip for scraper mode to show live browser)
    if request.searchMode != "scraper":
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {cache_key}")
            elapsed = time.time() - start_time
            return {"offers": cached_result, "latency_seconds": round(elapsed, 3), "cached": True}
    else:
        logger.info("Scraper mode: skipping cache to show live browser")

    # 2. Search (External APIs or Scraper)
    logger.info("Cache miss or scraper mode. Calling search...")
    # Call search skill
    raw_offers_result, warning_msg = search_offers(
        origin=request.origin,
        dest=request.destination,
        date=request.date,
        adults=request.adults,
        search_mode=request.searchMode
    )
    
    logger.info(f"search_offers returned {len(raw_offers_result)} raw offers")
    
    if not raw_offers_result:
        elapsed = time.time() - start_time
        return {"offers": [], "latency_seconds": round(elapsed, 3), "warning": warning_msg}

    # 3. Normalize
    normalized_offers = normalize_offers(raw_offers_result)
    
    # 4. Rank
    ranked_offers = rank_offers(normalized_offers)
    
    # 5. Cache Result (TTL 5 mins) - only for API mode
    if request.searchMode != "scraper":
        cache.set(cache_key, ranked_offers, ttl_seconds=300)
    
    elapsed = time.time() - start_time
    return {
        "offers": ranked_offers, 
        "latency_seconds": round(elapsed, 3), 
        "cached": False,
        "warning": warning_msg
    }

class ExplainRequest(BaseModel):
    target_offer: Offer
    comparison_offer: Offer | None = None

@app.post("/explain")
async def explain_flight(request: ExplainRequest):
    result = explain_choice(request.target_offer, request.comparison_offer)
    # result is now a dict {text: ..., usage: ...}
    return result

class AnalyzeRequest(BaseModel):
    offers: list[Offer]

@app.post("/analyze")
async def analyze_flights(request: AnalyzeRequest):
    try:
        from app.core.ai import analyze_top_offers
        return analyze_top_offers(request.offers)
    except Exception as e:
        logger.error(f"Analysis Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Scraper Configuration Endpoints ---

@app.get("/scraper/config")
async def get_scraper_config():
    """
    Get current scraper config and any pending AI suggestions.
    """
    import json
    import os
    
    config = {}
    suggestion = None
    
    config_path = "scraper_config.json"
    suggestion_path = "scraper_config_suggestion.json"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            pass
            
    if os.path.exists(suggestion_path):
        try:
            with open(suggestion_path, "r") as f:
                suggestion = json.load(f)
        except Exception:
            pass
            
    return {"config": config, "suggestion": suggestion}

@app.post("/scraper/config")
async def update_scraper_config(new_config: dict = Body(...)):
    """
    Update the scraper configuration.
    """
    import json
    import os
    from datetime import datetime
    
    config_path = "scraper_config.json"
    suggestion_path = "scraper_config_suggestion.json"
    
    # Update timestamp
    new_config["last_updated"] = datetime.now().isoformat()
    
    try:
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=2)
            
        # If successfully updated, remove the suggestion file if it exists
        # (Assuming user applied the suggestion)
        if os.path.exists(suggestion_path):
            os.remove(suggestion_path)
            
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.ENV}
