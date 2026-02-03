"""
ENA Travel Web Scraper
Scrapes flight data from kokunai.ena.travel
"""
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime
import re

logger = logging.getLogger(__name__)

def scrape_ena_flights(origin: str, dest: str, date: str, adults: int = 1, headless: bool = None, auto_close: bool = None):
    """
    Scrape flight offers from ENA Travel website
    
    Args:
        origin: Origin airport code (e.g., 'TYO')
        dest: Destination airport code (e.g., 'HIJ')
        date: Date in YYYY-MM-DD format
        adults: Number of adult passengers
        headless: Whether to run browser in headless mode (None = use config)
        auto_close: Whether to auto-close browser (None = use config)
    
    Returns:
        List of flight offer dictionaries compatible with Amadeus format
    """
    import concurrent.futures
    from app.config import settings
    
    # Use config defaults if not specified
    if headless is None:
        headless = settings.SCRAPER_HEADLESS
    if auto_close is None:
        auto_close = settings.SCRAPER_AUTO_CLOSE
    
    logger.info(f"Scraper settings: headless={headless}, auto_close={auto_close}")
    
    def _run_scraper():
        """Inner function to run scraper in separate thread"""
        results = []
        warning_msg = None
        
        # Format date for URL (YYYYMMDD)
        date_formatted = date.replace('-', '')
        
        # Build URL
        url = f"https://kokunai.ena.travel/internalairsearch?route={origin}-{dest}-{date_formatted}-nondirect&adt={adults}&chd=0&inf=0&airline=NH"
        
        logger.info(f"Scraping ENA Travel: {url}")
        
        try:
            with sync_playwright() as p:
                # Launch browser (headless or visible based on parameter)
                browser = p.chromium.launch(headless=headless)
                page = browser.new_page()
                
                # Navigate to search page
                page.goto(url, timeout=30000)
                
                # Wait for flight results to load
                try:
                    page.wait_for_selector('a#add_cart', timeout=15000)
                    logger.info("Flight results loaded successfully")
                except PlaywrightTimeout:
                    logger.warning("Timeout waiting for flight results selector")
                    browser.close()
                    return results
                
                # Load selectors from config
                import json
                import os
                
                config_path = "scraper_config.json"
                selectors = {
                    "container": "a#add_cart",
                    "flight_number": "li:nth-child(1) p:nth-child(2)",
                    "departure_time": "li:nth-child(2) p:first-child",
                    "arrival_time": "li:nth-child(4) p:first-child",
                    "price": "li:nth-child(7) p"
                }
                
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r") as f:
                            saved_config = json.load(f)
                            selectors.update(saved_config.get("selectors", {}))
                            logger.info("Loaded dynamic selectors from config")
                    except Exception as e:
                        logger.error(f"Failed to load config: {e}")
                
                # Extract flight data using DYNAMIC selectors
                flight_links = page.query_selector_all(selectors["container"])
                
                # --- AI FALLBACK CHECK ---
                if not flight_links:
                    logger.warning(f"No flight links found with selector '{selectors['container']}'. Attempting AI Fallback...")
                    # Get page content for AI
                    html_content = page.content()
                    from app.core.ai import extract_flights_from_html
                    
                    ai_results = extract_flights_from_html(html_content, origin, dest, date)
                    if ai_results:
                        logger.info(f"AI saved the day! Found {len(ai_results)} flights.")
                        
                        # --- SELF-HEALING: GENERATE FIX SUGGESTION (JSON) ---
                        logger.warning("⚠️ ALERT: Selectors failed. generating JSON config suggestion...")
                        try:
                            from app.core.ai import generate_json_selector_fix
                            suggestion_json = generate_json_selector_fix(html_content, ai_results)
                            if suggestion_json:
                                fix_file = "scraper_config_suggestion.json"
                                with open(fix_file, "w") as f:
                                    json.dump(suggestion_json, f, indent=2)
                                logger.warning(f"✅ Config suggestion saved to {fix_file}")
                                warning_msg = "Selectors updated by AI! Check Settings."
                        except Exception as e:
                            logger.error(f"Self-healing generation failed: {e}")
                        # ---------------------------------------------

                        for f in ai_results:
                            amadeus_format = build_amadeus_format(f, date)
                            results.append(amadeus_format)
                        
                        if auto_close: browser.close()
                        return results, warning_msg
                    else:
                        logger.warning("AI Fallback also failed.")
                # -------------------------
                
                logger.info(f"Found {len(flight_links)} flight results")
                
                for idx, link in enumerate(flight_links):
                    try:
                        # Extract data using dynamic selectors
                        flight_number_elem = link.query_selector(selectors["flight_number"])
                        dep_time_elem = link.query_selector(selectors["departure_time"])
                        arr_time_elem = link.query_selector(selectors["arrival_time"])
                        price_elem = link.query_selector(selectors["price"])
                        
                        if not all([flight_number_elem, dep_time_elem, arr_time_elem, price_elem]):
                            logger.warning(f"Skipping flight {idx}: missing elements")
                            continue
                        
                        flight_number = flight_number_elem.inner_text().strip()
                        dep_time = dep_time_elem.inner_text().strip()
                        arr_time = arr_time_elem.inner_text().strip()
                        price_text = price_elem.inner_text().strip()
                        
                        # Parse price (remove commas and 円)
                        price_clean = price_text.replace(',', '').replace('円', '').strip()
                        price =float(price_clean) if price_clean else 0
                        
                        # Extract airline code (usually first 2 letters of flight number)
                        airline_code = flight_number[:2] if len(flight_number) >= 2 else "NH"
                        flight_num = flight_number[2:] if len(flight_number) > 2 else flight_number
                        
                        # Build flight data
                        flight_data = {
                            "id": f"ENA_{idx+1}_{flight_number}",
                            "airline": airline_code,
                            "flight_number": flight_num,
                            "departure_time": dep_time,
                            "arrival_time": arr_time,
                            "price": price,
                            "origin": origin,
                            "destination": dest,
                            "date": date
                        }
                        
                        # Convert to Amadeus-compatible format
                        amadeus_format = build_amadeus_format(flight_data, date)
                        results.append(amadeus_format)
                        
                    except Exception as e:
                        logger.error(f"Error parsing flight {idx}: {e}")
                        continue
                
                # Keep browser open for a few seconds so user can see it
                import time
                if not headless:
                    logger.info("Keeping browser open for 3 seconds for visibility...")
                    time.sleep(3)
                
                # Close browser if auto_close is enabled, otherwise keep it open longer
                if auto_close:
                    browser.close()
                    logger.info("Browser closed")
                else:
                    logger.info("Browser left open (SCRAPER_AUTO_CLOSE=false)")
                    logger.info("Browser will remain open for 60 seconds before auto-closing...")
                    logger.info("You can manually close the browser window or press Ctrl+C to stop")
                    # Keep browser open for 60 seconds for inspection
                    time.sleep(60)
                    browser.close()
                    logger.info("Browser auto-closed after 60 seconds")
                
        except Exception as e:
            logger.error(f"ENA scraping error: {e}")
            # Optional: Add emergency HTML dump or AI rescue here if browser crashed
        
        logger.info(f"Successfully scraped {len(results)} flights from ENA Travel")
        return results, warning_msg
    
    # Run scraper in thread pool to avoid asyncio conflicts
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run_scraper)
        return future.result()


def build_amadeus_format(flight_data: dict, date: str) -> dict:
    """
    Convert scraped flight data to Amadeus-compatible format
    """
    # Parse times and build ISO datetime strings
    dep_time = flight_data['departure_time']  # e.g., "07:10"
    arr_time = flight_data['arrival_time']    # e.g., "08:35"
    
    dep_datetime = f"{date}T{dep_time}:00"
    arr_datetime = f"{date}T{arr_time}:00"
    
    # Calculate duration in minutes
    dep_h, dep_m = map(int, dep_time.split(':'))
    arr_h, arr_m = map(int, arr_time.split(':'))
    duration_mins = (arr_h * 60 + arr_m) - (dep_h * 60 + dep_m)
    
    # Format as ISO 8601 duration
    hours = duration_mins // 60
    minutes = duration_mins % 60
    duration_str = f"PT{hours}H{minutes}M"
    
    return {
        "_source": "ena_scraper",
        "id": flight_data['id'],
        "type": "flight-offer",
        "price": {
            "total": str(flight_data['price']),
            "currency": "JPY"
        },
        "validatingAirlineCodes": [flight_data['airline']],
        "itineraries": [{
            "duration": duration_str,
            "segments": [{
                "departure": {
                    "iataCode": flight_data['origin'],
                    "at": dep_datetime
                },
                "arrival": {
                    "iataCode": flight_data['destination'],
                    "at": arr_datetime
                },
                "carrierCode": flight_data['airline'],
                "number": flight_data['flight_number'],
                "duration": duration_str,
                "aircraft": {"code": "738"}  # Default, could be extracted if available
            }]
        }],
        "numberOfBookableSeats": 9,  # Default, not available from ENA page
        "travelerPricings": [{
            "fareDetailsBySegment": [{
                "cabin": "ECONOMY"  # Default
            }]
        }]
    }
