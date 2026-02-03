"""
Test ENA Travel scraper
"""
import sys
sys.path.insert(0, '/Users/hajime/work/nagae/air_ticket/backend')

from app.skills.scrape_ena import scrape_ena_flights

# Test with real parameters
results = scrape_ena_flights("TYO", "HIJ", "2026-02-06", 1)

print(f"Found {len(results)} flights")
for r in results:
    print(r)
