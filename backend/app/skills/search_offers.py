from amadeus import Client, ResponseError
from app.config import settings
from serpapi import GoogleSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Amadeus Client
try:
    amadeus = Client(
        client_id=settings.AMADEUS_CLIENT_ID,
        client_secret=settings.AMADEUS_CLIENT_SECRET,
        hostname=settings.AMADEUS_HOSTNAME
    )
except Exception as e:
    logger.error(f"Failed to initialize Amadeus client: {e}")
    amadeus = None

# Common City Code Mapping (Simple Fallback)
CITY_MAP = {
    # Japan
    "東京": "TYO", "TOKYO": "TYO", "TYO": "TYO", "羽田": "HND", "HANEDA": "HND", "HND": "HND", "成田": "NRT", "NARITA": "NRT", "NRT": "NRT",
    "大阪": "OSA", "OSAKA": "OSA", "OSA": "OSA", "関西": "KIX", "KIX": "KIX", "ITAMI": "ITM", "伊丹": "ITM", "ITM": "ITM",
    "札幌": "SPK", "SAPPORO": "SPK", "SPK": "SPK", "千歳": "CTS", "CTS": "CTS",
    "福岡": "FUK", "FUKUOKA": "FUK", "FUK": "FUK",
    "広島": "HIJ", "HIROSHIMA": "HIJ", "HIJ": "HIJ",
    "沖縄": "OKA", "OKINAWA": "OKA", "OKA": "OKA", "那覇": "OKA",
    "名古屋": "NGO", "NAGOYA": "NGO", "NGO": "NGO",
    # International (Common)
    "LOS ANGELES": "LAX", "LAX": "LAX", "洛杉矶": "LAX", "ロサンゼルス": "LAX",
    "NEW YORK": "NYC", "NYC": "NYC", "ニューヨーク": "NYC",
    "LONDON": "LON", "ロンドン": "LON",
    "PARIS": "PAR", "パリ": "PAR",
    "HONOLULU": "HNL", "ホノルル": "HNL"
}

# Runtime Cache for looked up cities
DYNAMIC_CITY_CACHE = {}

def resolve_code(input_str: str) -> str:
    """
    Convert user input to IATA Code.
    1. Check Static Map
    2. Check Cache
    3. Call Amadeus Location Search
    """
    if not input_str:
        return ""
    
    clean_str = input_str.strip().upper()
    
    # 1. Static Map
    if clean_str in CITY_MAP:
        return CITY_MAP[clean_str]
    
    # 2. Dynamic Cache
    if clean_str in DYNAMIC_CITY_CACHE:
        return DYNAMIC_CITY_CACHE[clean_str]

    # 3. Amadeus Location Search (Fallback)
    if amadeus:
        try:
            logger.info(f"Resolving unknown city code via API: {clean_str}")
            # Import Location here to avoid circular/early import issues if any
            from amadeus import Location
            
            response = amadeus.reference_data.locations.get(
                keyword=clean_str,
                subType=[Location.CITY, Location.AIRPORT]
            )
            
            if response.data:
                # Take the first result's IATA code
                found_code = response.data[0]['iataCode']
                logger.info(f"Resolved {clean_str} -> {found_code}")
                DYNAMIC_CITY_CACHE[clean_str] = found_code
                return found_code
                
        except Exception as e:
            logger.warning(f"Failed to resolve city via API: {e}")
            
    # Fallback: Assume it is a code
    return clean_str

def search_offers(origin: str, dest: str, date: str, adults: int = 1, search_mode: str = "api", trip_type: str = "oneway", time_range: str = None, flexible_ticket: bool = False) -> tuple[list[dict], str | None]:
    """
    Orchestrate the search process.
    """
    logger.info(f"Searching offers: {origin}->{dest} on {date} (Mode: {search_mode})")
    
    
    # Resolve cities to airport codes using comprehensive mapping
    origin_code = resolve_code(origin)
    dest_code = resolve_code(dest)

    
    # 1. Scraper Mode (ANA Official)
    if search_mode == "scraper":
        logger.info(f"[SCRAPER MODE] Using ANA Official scraper: {origin}({origin_code})->{dest}({dest_code}) on {date}, trip_type={trip_type}")
        results = []
        warning = None
        try:
            from app.skills.scrape_ana import scrape_ana_flights
            # Pass new filters to scraper
            ana_results, ana_warning = scrape_ana_flights(
                origin_code, dest_code, date, adults, 
                trip_type=trip_type,
                time_range=time_range, 
                flexible_ticket=flexible_ticket
            )
            results.extend(ana_results)
            warning = ana_warning
            logger.info(f"[SCRAPER MODE] ANA scraper found {len(ana_results)} offers")
        except Exception as e:
            logger.error(f"[SCRAPER MODE] ANA scraper failed: {e}")
            warning = f"ANA Scraper Failed: {e}"
        
        return results, warning
  # Return scraper results and warning
    
    # Mode: API - Use Google Flights (SerpApi) as primary
    logger.info(f"[API MODE] Using API search: {origin}({origin_code})->{dest}({dest_code}) on {date}")
    results = [] # Initialize results list

    
    # 1. Try SerpApi (Google Flights) - PRIMARY
    if settings.SERPAPI_KEY:
        try:
            logger.info(f"[API MODE] Searching SerpApi (Google Flights)...")
            params = {
                "engine": "google_flights",
                "departure_id": origin_code,
                "arrival_id": dest_code,
                "outbound_date": date,
                "adults": adults,
                "currency": "JPY", # Enforce JPY
                "hl": "ja",        # Japanese locale
                "api_key": settings.SERPAPI_KEY,
                "type": "2" if trip_type == "oneway" else "1" # 2=OneWay, 1=RoundTrip
            }
            
            if trip_type == "roundtrip":
                 # Add return date if needed, but current signature doesn't support it fully yet
                 # For now defaulting to one-way logic or simple parameter pass key
                 pass
            
            search = GoogleSearch(params)
            serpapi_data = search.get_dict()
            
            # Extract 'best_flights' or 'flights'
            # Google Flights API structure usually has 'best_flights' and 'other_flights'
            flight_lists = []
            if "best_flights" in serpapi_data:
                flight_lists.extend(serpapi_data["best_flights"])
            if "other_flights" in serpapi_data:
                flight_lists.extend(serpapi_data["other_flights"])
                
            if not flight_lists:
                logger.warning(f"[API MODE] SerpApi returned 0 flights.")
            
            for flight in flight_lists:
                flight['_source'] = 'serpapi'
                results.append(flight)
                
            logger.info(f"[API MODE] SerpApi found {len(results)} offers")
            
        except Exception as e:
            logger.error(f"[API MODE] SerpApi Error: {e}")
            
    # 2. Amadeus (Legacy/Backup - Disabled for now as per request)
    """
    if not results and amadeus:
        try:
            logger.info(f"[API MODE] Searching Amadeus API (Backup)...")
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin_code,
                destinationLocationCode=dest_code,
                departureDate=date,
                adults=adults,
                currencyCode="JPY",
                max=50
            )
            if response.data:
                amadeus_offers = response.data
                for offer in amadeus_offers:
                    offer['_source'] = 'amadeus'
                results.extend(amadeus_offers)
                logger.info(f"[API MODE] Amadeus found {len(amadeus_offers)} offers")
        except ResponseError as e:
            logger.error(f"[API MODE] Amadeus API Error: {e.code}")
        except Exception as e:
            logger.error(f"[API MODE] Amadeus Unexpected Error: {e}")
    """
    
    logger.info(f"[API MODE] Total API results: {len(results)}")
    return results, None
