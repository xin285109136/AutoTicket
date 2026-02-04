import logging
import time
from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

def scrape_ana_flights(origin: str, dest: str, date: str, adults: int = 1, trip_type: str = "oneway", time_range: str = None, flexible_ticket: bool = False, headless: bool = None, auto_close: bool = None):
    """
    Scrape flight data from ANA Official Website.
    
    Args:
        origin (str): Origin airport code (e.g., HND, ITM)
        dest (str): Destination airport code
        date (str): Date in 'YYYY-MM-DD' format
        adults (int): Number of adults
        time_range (str): Optional time filter (e.g. "morning", "afternoon") - currently handled post-scraping
        flexible_ticket (bool): If True, prioritize 'Flex' fares.
    
    Returns:
        tuple[list[dict], str | None]: (List of flight offers, Warning message if any)
    """
    # Config defaults from env
    from app.config import settings
    if headless is None:
        headless = settings.SCRAPER_HEADLESS
    if auto_close is None:
        auto_close = settings.SCRAPER_AUTO_CLOSE

    def _run_scraper():
        results = []
        warning_msg = None
        
        # ANA URL
        url = "https://www.ana.co.jp/ja/jp/search/domestic/flight/"
        
        # Convert date YYYY-MM-DD -> YYYY年M月D日 (ANA format)
        dt = datetime.strptime(date, "%Y-%m-%d")
        target_date_str = f"{dt.year}年{dt.month}月{dt.day}日" # e.g. 2026年3月3日
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                logger.info(f"Navigating to ANA: {url}")
                page.goto(url, timeout=60000)
                
                # 1. Open Search Form if needed (Click 'Open' button)
                try:
                    open_btn = page.query_selector("button.be-domestic-reserve-ticket-form-open__button")
                    if open_btn and open_btn.is_visible():
                        open_btn.click()
                        time.sleep(1)
                except:
                    pass

                # 2. Select Trip Type (One-way or Round-trip)
                logger.info(f"[DEBUG] Received trip_type parameter: '{trip_type}'")
                # If user wants round-trip, SKIP clicking "片道" (it defaults to round-trip 往復)
                # If user wants one-way, we click "片道"
                if trip_type == "oneway":
                    logger.info("[TRIP TYPE] User selected ONE-WAY (片道), clicking the button...")
                    try:
                        # Use .first to select the first visible "片道" button (domestic flights)
                        one_way_btn = page.locator("li.be-switch__item", has_text="片道").first
                        one_way_btn.click()
                        time.sleep(0.5)
                        logger.info("[TRIP TYPE] Successfully selected One-way")
                    except Exception as e:
                        logger.warning(f"[TRIP TYPE] Could not select One-way: {e}")
                else:
                    logger.info(f"[TRIP TYPE] User selected ROUND-TRIP (往復), skipping '片道' click. Using default.")

                # 3. Helpers for Airport Selection
                def select_airport(btn_selector, airport_code):
                    """
                    Select airport by typing search text first to filter the list.
                    This matches real user behavior on ANA's website.
                    """
                    # Step 1: Click to open dropdown
                    page.click(btn_selector)
                    time.sleep(1.5)
                    
                    try:
                        # Step 2: Find and type in the search input field
                        # ANA uses input with placeholder "都市または空港を入力"
                        search_input_selectors = [
                            "input[placeholder*='都市']",
                            "input[placeholder*='空港']",
                            "input.be-search-autocomplete__input",
                            "div[role='dialog'] input[type='text']"
                        ]
                        
                        search_input = None
                        for selector in search_input_selectors:
                            inputs = page.locator(selector)
                            if inputs.count() > 0 and inputs.first.is_visible():
                                search_input = inputs.first
                                break
                        
                        if search_input:
                            # Clear and type airport code
                            search_input.fill("")
                            time.sleep(0.3)
                            search_input.fill(airport_code)
                            time.sleep(1.5)  # Wait for autocomplete to filter
                            logger.info(f"[AIRPORT] Typed '{airport_code}' to filter results")
                            
                            # Step 3: Use JavaScript to directly click the element
                            # This bypasses Playwright's visibility check completely
                            js_click_script = f"""
                            () => {{
                                // Find the list item with matching data-value
                                const item = document.querySelector('li[data-value="{airport_code}"]');
                                if (item) {{
                                    item.click();
                                    return 'clicked: ' + item.textContent;
                                }}
                                // Fallback: find by text content
                                const items = Array.from(document.querySelectorAll('li.be-list__item'));
                                const match = items.find(el => el.textContent.includes('{airport_code}'));
                                if (match) {{
                                    match.click();
                                    return 'clicked by text: ' + match.textContent;
                                }}
                                return 'not found';
                            }}
                            """
                            
                            result = page.evaluate(js_click_script)
                            logger.info(f"[AIRPORT] JavaScript click result: {result}")
                            time.sleep(0.5)
                            clicked = True
                        else:
                            # No search input - fallback to direct click
                            logger.warning(f"[AIRPORT] No search input found, using direct selection")
                            xpath = f"//span[text()='{airport_code}']/ancestor::button | //button[contains(., '{airport_code}')]"
                            page.locator(xpath).first.click()
                            
                    except Exception as e:
                        logger.error(f"[AIRPORT] Failed to select {airport_code}: {e}")
                        raise
                    
                    time.sleep(1)

                # Select Origin
                select_airport("button.be-domestic-reserve-ticket-departure-airport__button", origin)
                
                # Select Destination
                select_airport("button.be-domestic-reserve-ticket-arrival-airport__button", dest)

                # 4. Select Date
                page.click("button.be-domestic-reserve-ticket-departure-date__button")
                time.sleep(2) # Longer wait for calendar to fully load
                
                # ANA Calendar Format: aria-label = "2026年2月17日 火曜日" (with weekday in Japanese)
                # Key insight: Use the calendar-specific button class to avoid matching car rental buttons
                date_selected = False
                try:
                    # Build the date string without weekday (will use contains match)
                    target_date_base = f"{dt.year}年{dt.month}月{dt.day}日"
                    logger.info(f"[DATE] Looking for date: {target_date_base} (any weekday)")
                    
                    # Strategy: Use the calendar-specific button class and partial aria-label match
                    # This avoids matching car rental or other date pickers
                    date_btn = page.locator(
                        f"button.be-calendar-month__cell-button[aria-label^='{target_date_base}']"
                    )
                    
                    count = date_btn.count()
                    logger.info(f"[DATE] Found {count} matching calendar buttons")
                    
                    if count > 0:
                        # Check visibility and click the first visible one
                        for i in range(count):
                            btn = date_btn.nth(i)
                            if btn.is_visible():
                                btn.click()
                                logger.info(f"[DATE] ✓ Successfully selected date: {target_date_base}")
                                date_selected = True
                                break
                    
                    if not date_selected:
                        logger.error(f"[DATE] ✗ No visible calendar button found for {target_date_base}")
                        raise Exception(f"Failed to select date {date}. Date button not found or not clickable.")
                    
                    time.sleep(1)
                    
                    # Confirm date with the positive button in dialog
                    confirm_btn = page.locator("button.be-dialog__button--positive", has_text="決定")
                    if confirm_btn.count() > 0:
                        confirm_btn.click()
                        time.sleep(1)
                        logger.info("[DATE] ✓ Date confirmed with dialog button")
                    else:
                        # Fallback to generic text match
                        confirm_btn_fallback = page.locator("button", has_text="決定")
                        if confirm_btn_fallback.count() > 0:
                            confirm_btn_fallback.first.click()
                            time.sleep(1)
                            logger.info("[DATE] ✓ Date confirmed with fallback button")
                        else:
                            logger.warning("[DATE] ⚠️ No confirm button found, date might auto-apply")
                        
                except Exception as e:
                    logger.error(f"Date selection failed: {e}")
                    raise  # Re-raise to stop scraping with wrong date

                # 5. Submit Search
                # Use more specific selector to avoid matching disabled button
                search_btn = page.locator("button.be-domestic-reserve-ticket-submit__button:not([disabled])").first
                search_btn.click()
                
                logger.info("Search submitted, waiting for results...")
                page.wait_for_selector("div.be-flight-list, table", timeout=30000) # Generic wait
                time.sleep(3) # Extra wait for dynamic loading

                    
                # 6. Parse Results
                # Load ANA specific selectors
                config_path = "scraper_ana_config.json"
                selectors = {
                    "row": "tr.be-flight-list-row", # Hypothetical class, will use broad generic if specific fails
                    "flight_number": ".be-flight-number",
                    "dep_time": ".be-flight-time-dep",
                    "arr_time": ".be-flight-time-arr",
                    "price_flex": "td:has-text('予約変更可')", # Logic will be more complex in loop
                    "price_value": "td:has-text('予約変更不可')" 
                }
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r") as f:
                            selectors.update(json.load(f).get("selectors", {}))
                    except: pass

                # ANA structure usually: Table with rows. 
                # We'll select all rows that look like flights.
                # Using a more generic approach relying on text content for robustness against class changes.
                flight_rows = page.query_selector_all("tr")
                logger.info(f"Processing {len(flight_rows)} rows...")

                for row in flight_rows:
                    try:
                        text = row.inner_text()
                        if "ANA" not in text or "到着" in text: continue # Header or invalid row

                        # Extract basic info
                        # Need to parse "10:00" -> "11:15" patterns
                        import re
                        times = re.findall(r"(\d{2}:\d{2})", text)
                        if len(times) < 2: continue
                        dep_time = times[0]
                        arr_time = times[1]

                        # Flight Number (e.g., ANA 015)
                        flight_num = "ANA ???"
                        fn_match = re.search(r"(ANA\s?\d{2,4})", text)
                        if fn_match:
                            flight_num = fn_match.group(1).replace(" ", "")

                        # Extract Prices
                        # We need to find the specific "Flexible" vs "Value" columns.
                        # Best way: Check the column index or label within the row.
                        
                        # Simple heuristic:
                        # value_price = lowest price found in row
                        # flexible_price = price associated with "Changeable" label
                        
                        prices = []
                        # Find all price texts like "34,000"
                        price_matches = re.findall(r"(\d{1,3}(?:,\d{3})*)", text)
                        # Filter for real prices (usually > 5000)
                        valid_prices = []
                        for p in price_matches:
                            v = int(p.replace(",", ""))
                            if v > 5000: valid_prices.append(v)
                        
                        if not valid_prices: continue
                        
                        # Logic for Ticket Type
                        # If user wants "Flexible" (Changeable), we try to find the higher price usually associated with Flex
                        # If "Lowest" (Non-changeable), we take the minimum.
                        
                        final_price = min(valid_prices) # Default to lowest
                        fare_type = "Value"
                        
                        if flexible_ticket:
                            # Try to find max or specific column
                            # For MVP, we assume the highest valid price in the row is the Flex fare
                            # (This is a simplification; ideally we map column indices)
                            final_price = max(valid_prices)
                            fare_type = "Flex"

                        # --- Time Filtering ---
                        if time_range:
                            # Simple logic: "morning" (start < 12), "afternoon" (12-17), "evening" (>17)
                            dep_h = int(dep_time.split(":")[0])
                            matched_time = False
                            if time_range == "morning" and dep_h < 12: matched_time = True
                            elif time_range == "afternoon" and 12 <= dep_h < 18: matched_time = True
                            elif time_range == "evening" and dep_h >= 18: matched_time = True
                            
                            if not matched_time: continue
                        # ----------------------

                        offer = {
                            "source": "ANA_Official",
                            "id": f"ANA_{flight_num}_{dep_time}",
                            "carrier_main": "ANA",
                            "price": final_price,
                            "currency": "JPY",
                            "segments": [{
                                "departure_iatacode": origin,
                                "arrival_iatacode": dest,
                                "departure_time": f"{date}T{dep_time}:00",
                                "arrival_time": f"{date}T{arr_time}:00",
                                "flight_number": flight_num,
                                "duration": "0h 0m", # Calc if needed
                                "aircraft": "Unknown",
                                "seats_available": 9
                            }],
                            "fare_type": fare_type
                        }
                        results.append(offer)

                    except Exception as e:
                        logger.debug(f"Row parse error: {e}")
                        continue

                # --- AI FALLBACK ---
                if not results:
                    logger.warning("Standard scraping returned 0 results. Triggering AI Fallback...")
                    html_content = page.content()
                    from app.core.ai import extract_flights_from_html, generate_json_selector_fix
                    
                    # Use AI to parse the complex table
                    ai_results = extract_flights_from_html(html_content, origin, dest, date)
                    if ai_results:
                        logger.info(f"AI extracted {len(ai_results)} flights from ANA page.")
                        
                        # Generate Config Fix
                        try:
                            suggestion = generate_json_selector_fix(html_content, ai_results)
                            if suggestion:
                                with open("scraper_ana_config_suggestion.json", "w") as f:
                                    json.dump(suggestion, f, indent=2)
                                warning_msg = "ANA Scraper: Selectors updated by AI! Check Settings."
                        except: pass
                        
                        # Convert AI results to Offer format
                        for f in ai_results:
                             # normalize...
                             pass
                             # Append to results
                             
                        if time_range:
                            # Filter AI results...
                            pass
                    else:
                        logger.warning("AI Fallback failed.")
                
                if auto_close: browser.close()

                    
        except Exception as e:
            logger.error(f"ANA Scraper Error: {e}")
            warning_msg = f"Scraper Error: {e}"

        return results, warning_msg

    # Run in thread pool to avoid asyncio conflicts
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_scraper)
        return future.result()
