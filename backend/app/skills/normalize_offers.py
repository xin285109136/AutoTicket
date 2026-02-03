from app.models import Offer, Segment
from datetime import datetime
import re

def parse_duration(pt_duration: str) -> int:
    """Parse ISO 8601 duration (PT1H30M) to minutes."""
    # Amadeus uses PTxxHxxM format
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', pt_duration)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    m = int(match.group(2) or 0)
    return h * 60 + m

def extract_cabin(raw: dict) -> str:
    """Safely extract cabin class."""
    try:
        tps = raw.get('travelerPricings', [])
        if not tps: return "ECONOMY"
        fds = tps[0].get('fareDetailsBySegment', [])
        if not fds: return "ECONOMY"
        return fds[0].get('cabin', "ECONOMY")
    except:
        return "ECONOMY"

def normalize_amadeus_offer(raw: dict) -> Offer:
    segments = []
    itinerary = raw['itineraries'][0] # Assuming one-way for now or logic handling
    # If multiple itineraries (return flight), this needs loop.
    # For now, let's flatten all segments if just one itinerary or sum up logic.
    # Simplified: Taking first itinerary which corresponds to outbound for one-way.
    
    total_duration = parse_duration(itinerary['duration'])
    
    for seg in itinerary['segments']:
        segments.append(Segment(
            departure_iata=seg['departure']['iataCode'],
            arrival_iata=seg['arrival']['iataCode'],
            departure_time=datetime.fromisoformat(seg['departure']['at']),
            arrival_time=datetime.fromisoformat(seg['arrival']['at']),
            carrier_code=seg['carrierCode'],
            flight_number=seg['number'],
            duration_minutes=parse_duration(seg['duration']),
            # Rich Data Extraction (Safe access)
            terminal=seg['departure'].get('terminal'),
            aircraft=seg.get('aircraft', {}).get('code'),
            cabin_class=extract_cabin(raw),
            seats_available=raw.get('numberOfBookableSeats')
        ))
        
    # Currency Conversion Removed - handled by frontend
    price = float(raw['price']['total'])
    currency = raw['price']['currency']

    return Offer(
        id=raw['id'],
        source='amadeus',
        price=price, 
        currency=currency,
        total_duration_minutes=total_duration,
        segments=segments,
        carrier_main=raw['validatingAirlineCodes'][0] if raw.get('validatingAirlineCodes') else segments[0].carrier_code,
        stops=len(segments) - 1
    )

def normalize_serpapi_offer(raw: dict) -> Offer:
    segments = []
    # SerpApi structure calls segments 'flights'
    for flight in raw.get('flights_cluster', [{}])[0].get('flights', []) if 'flights_cluster' in raw else raw.get('flights', []):
         # Note: SerpApi structure varies. Assuming 'flights' list in raw object from search_offers extraction
         pass
    
    # Re-evaluating SerpApi structure based on documentation/experience
    # search_offers extracts 'best_flights' items.
    # Item structure:
    # {
    #   "flights": [ { "departure_airport": {...}, "arrival_airport": {...}, ... } ],
    #   "total_duration": 123,
    #   "price": 100, ...
    # }
    
    current_flights = raw.get('flights', [])
    for f in current_flights:
        segments.append(Segment(
            departure_iata=f.get('departure_airport', {}).get('id'),
            arrival_iata=f.get('arrival_airport', {}).get('id'),
            departure_time=datetime.strptime(f['departure_time'], '%Y-%m-%d %H:%M') if 'departure_time' in f else datetime.now(), # Format might vary
            arrival_time=datetime.strptime(f['arrival_time'], '%Y-%m-%d %H:%M') if 'arrival_time' in f else datetime.now(),
            carrier_code=f.get('airline_code', ''),
            flight_number=f.get('flight_number', ''),
            duration_minutes=f.get('duration', 0),
            cabin_class=f.get('travel_class')
        ))

    return Offer(
        id=raw.get('token', 'serp_' + str(raw.get('price'))), # SerpApi might not have ID
        source='serpapi',
        price=float(raw.get('price', 0)),
        currency='JPY', # Forced in search params
        total_duration_minutes=raw.get('total_duration', 0),
        segments=segments,
        carrier_main=segments[0].carrier_code if segments else 'UNK',
        stops=len(segments) - 1
    )

def normalize_offers(raw_offers: list[dict]) -> list[Offer]:
    normalized = []
    for raw in raw_offers:
        try:
            source = raw.get('_source')
            if source == 'amadeus':
                normalized.append(normalize_amadeus_offer(raw))
            elif source == 'serpapi':
                normalized.append(normalize_serpapi_offer(raw))
            elif source == 'ena_scraper':
                # ENA scraper data is already in Amadeus-compatible format
                # Just normalize it like Amadeus data
                normalized.append(normalize_amadeus_offer(raw))
        except Exception as e:
            # Skip malformed offers but log in real prod
            print(f"Error normalizing offer from {raw.get('_source')}: {e}")
            continue
    return normalized
