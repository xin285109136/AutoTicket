from app.models import Offer
from typing import List, Dict, Optional

def calculate_score(offer: Offer, prefs: Dict = None) -> float:
    """
    Calculate a score for the offer based on rules.
    Higher score is better.
    Base score: 1000.
    """
    score = 1000.0
    breakdown = {}
    
    prefs = prefs or {}
    
    # 1. Price Factor
    # Penalty: -1 point per 1000 JPY (arbitrary scaling)
    price_penalty = offer.price / 1000.0
    score -= price_penalty
    breakdown['price'] = f"-{price_penalty:.1f} (Price: {offer.price})"

    # 2. Duration Factor
    # Penalty: -1 point per 10 minutes
    duration_penalty = offer.total_duration_minutes / 10.0
    score -= duration_penalty
    breakdown['duration'] = f"-{duration_penalty:.1f} (Duration: {offer.total_duration_minutes}m)"

    # 3. Stops Factor
    # Penalty: -50 points per stop
    stops_penalty = offer.stops * 50.0
    score -= stops_penalty
    breakdown['stops'] = f"-{stops_penalty:.1f} ({offer.stops} stops)"

    # 4. Carrier Preference (Example)
    preferred_carrier = prefs.get('carrier')
    if preferred_carrier and offer.carrier_main == preferred_carrier:
        score += 100
        breakdown['carrier'] = f"+100 (Preferred: {preferred_carrier})"

    offer.score = score
    offer.score_breakdown = breakdown
    return score

def rank_offers(offers: List[Offer], prefs: Dict = None) -> List[Offer]:
    """
    Score and sort offers. Returns the sorted list.
    """
    for offer in offers:
        calculate_score(offer, prefs)
    
    # Sort descending by score
    return sorted(offers, key=lambda x: x.score, reverse=True)
