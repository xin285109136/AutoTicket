"""
Test visible scraper
"""
import sys
import logging
sys.path.insert(0, '/Users/hajime/work/nagae/air_ticket/backend')

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

from app.skills.scrape_ena import scrape_ena_flights

print("=" * 60)
print("Testing ENA scraper with VISIBLE browser (headless=False)")
print("=" * 60)

# Test with visible browser
results = scrape_ena_flights("TYO", "OSA", "2026-02-20", 1, headless=False)

print(f"\n{'='*60}")
print(f"Results: Found {len(results)} flights")
print(f"{'='*60}")

if results:
    print("\nFirst flight details:")
    import json
    print(json.dumps(results[0], indent=2, ensure_ascii=False))
else:
    print("\nNo results returned - check error logs above")
