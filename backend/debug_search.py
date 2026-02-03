from serpapi import GoogleSearch
import json
import os
from dotenv import load_dotenv

load_dotenv()

def debug_serpapi():
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("No SERPAPI_KEY found")
        return

    params = {
        "engine": "google_flights",
        "departure_id": "TYO",
        "arrival_id": "OSA",
        "outbound_date": "2026-02-06",
        "adults": 1,
        "currency": "JPY",
        "hl": "en",
        "type": "2",  # One-Way
        "api_key": api_key
    }
    
    print(f"Searching SerpApi with params: {params}")
    
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
        
        print("Keys in response:", data.keys())
        
        if 'error' in data:
            print("Error in response:", data['error'])
            
        best = data.get('best_flights', [])
        other = data.get('other_flights', [])
        
        print(f"Best flights count: {len(best)}")
        print(f"Other flights count: {len(other)}")
        
        if not best and not other:
            print("No flights found. Metadata:", json.dumps(data.get('search_metadata', {}), indent=2))
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_serpapi()
