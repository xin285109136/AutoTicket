from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Segment(BaseModel):
    departure_iata: str
    arrival_iata: str
    departure_time: datetime
    arrival_time: datetime
    carrier_code: str
    flight_number: str
    duration_minutes: int
    
    # Rich Data
    cabin_class: Optional[str] = "ECONOMY"
    aircraft: Optional[str] = None # e.g. "B787"
    terminal: Optional[str] = None # e.g. "T2"
    seats_available: Optional[int] = None # e.g. 9
    carrier_name: Optional[str] = None # e.g. "All Nippon Airways"

class Offer(BaseModel):
    id: str  # Unique ID from provider (or generated)
    source: str  # 'amadeus' or 'serpapi'
    price: float
    currency: str
    total_duration_minutes: int
    segments: List[Segment]
    carrier_main: str  # Main carrier (e.g., NH for ANA)
    stops: int
    
    # Internal scoring fields
    score: Optional[float] = 0.0
    score_breakdown: Optional[dict] = {}

    class Config:
        from_attributes = True
