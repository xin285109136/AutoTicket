import google.generativeai as genai
from openai import OpenAI
from app.config import settings
from app.models import Offer
import logging

logger = logging.getLogger(__name__)

# Initialize Clients
gemini_model = None
openai_client = None

def init_ai():
    global gemini_model, openai_client
    
    # 1. Gemini Init
    if settings.GOOGLE_API_KEY:
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            # Use 'gemini-pro' as it is widely available, or 'gemini-1.5-flash' if enabled
            # Try 'gemini-1.5-flash' first, but if error 404 seen, use 'gemini-pro'
            gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        except Exception as e:
            logger.warning(f"Gemini Init Warning: {e}")
    
    # 2. OpenAI Init
    if settings.OPENAI_API_KEY:
        try:
            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception as e:
            logger.warning(f"OpenAI Init Warning: {e}")

# Call init on module load
init_ai()

def explain_with_openai(prompt: str) -> dict:
    if not openai_client:
        return {"text": "OpenAI API Key missing.", "usage": None}
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant. Reply in Japanese."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        content = response.choices[0].message.content
        usage = response.usage
        
        # Cost Calc (GPT-4o-mini approx prices)
        # Input: $0.15 / 1M tokens, Output: $0.60 / 1M tokens
        # 1 USD = 150 JPY
        input_cost_usd = (usage.prompt_tokens / 1_000_000) * 0.15
        output_cost_usd = (usage.completion_tokens / 1_000_000) * 0.60
        total_jpy = (input_cost_usd + output_cost_usd) * 150
        
        return {
            "text": content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost_jpy": round(total_jpy, 4)
            }
        }
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        return {"text": f"OpenAI Error: {e}", "usage": None}

def explain_with_gemini(prompt: str) -> dict:
    if not gemini_model:
        return {"text": "Gemini API Key missing.", "usage": None}
    try:
        # Gemini 1.5 Flash Pricing (approx)
        # Free tier is free, Paid tier: Input $0.075/1M, Output $0.3/1M (Checking updated pricing)
        # Using Paid tier assumption for calc:
        response = gemini_model.generate_content(prompt)
        text = response.text
        
        # Gemini usage access varies by library version, basic mock if unavailable
        # Assuming usage available or estimating
        # Note: genai python SDK usage metadata access is sometimes limited in older versions
        # Mocking usage for Gemini Free Tier or simple estimation
        
        estimated_input = len(prompt) / 4
        estimated_output = len(text) / 4
        total_tokens = int(estimated_input + estimated_output)
        
        # Mock Cost (Flash is very cheap, often free for low usage)
        cost_jpy = (total_tokens / 1_000_000) * 0.10 * 150 # Rough estimate
        
        return {
            "text": text,
            "usage": {
                "total_tokens": total_tokens,
                "cost_jpy": round(cost_jpy, 4),
                "note": "Estimated (Gemini)"
            }
        }
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return {"text": f"Gemini Error: {e}", "usage": None}

def explain_choice(offer_a: Offer, offer_b: Offer = None) -> dict:
    """
    Generate explanation using the configured provider. Returns dict with text and usage.
    """
    
    prompt = f"""
    Please briefly explain why this flight option is good in 2-3 sentences.
    Focus on value, time, and convenience. Use Japanese.

    Option A:
    Airline: {offer_a.carrier_main}
    Price: {offer_a.price} {offer_a.currency}
    Duration: {offer_a.total_duration_minutes} min
    Stops: {offer_a.stops}
    Score Breakdown: {offer_a.score_breakdown}
    """
    # ... (Prompt construction same as before) ...
    if offer_b:
        prompt += f"""
        Option B (Comparison):
        Airline: {offer_b.carrier_main}
        Price: {offer_b.price} {offer_b.currency}
        Duration: {offer_b.total_duration_minutes} min
        Stops: {offer_b.stops}
        
        Compare A against B. Highlight why A might be preferred.
        """

    provider = settings.AI_PROVIDER.lower()
    
    if provider == "openai":
        return explain_with_openai(prompt)
    else:
        return explain_with_gemini(prompt)

def analyze_top_offers(offers: list[Offer]) -> dict:
    """
    Analyze the top 5 offers globally.
    """
    # 1. Prepare Summary Context
    top_5 = offers[:5]
    summary_text = ""
    for idx, o in enumerate(top_5):
        summary_text += f"""
        Option {idx+1}: {o.carrier_main} | {o.price:,.0f} {o.currency}
        Time: {o.segments[0].departure_time} -> {o.segments[-1].arrival_time} (Duration: {o.total_duration_minutes}m)
        Stops: {o.stops} | Aircraft: {o.segments[0].aircraft} | Seats: {o.segments[0].seats_available}
        """

    prompt = f"""
    You are a professional travel agent. Analyze these top flight options for the user.
    Output a structured recommendation in Japanese.

    Flight Options:
    {summary_text}

    Please provide:
    1. 🏆 **Best Overall**: Which one and why?
    2. 💰 **Best Value**: If different from above.
    3. ⚡ **Fastest/Most Convenient**: Best for time.
    4. ⚠️ **Important Notes**: Any warnings about terminals, tight connections, or low seats?
    
    Keep it concise and helpful. formatting with Markdown.
    """

    provider = settings.AI_PROVIDER.lower()

    if provider == "openai":
        return explain_with_openai(prompt)
    else:
        return explain_with_gemini(prompt)

def extract_flights_from_html(html_content: str, origin: str, dest: str, date: str) -> list[dict]:
    """
    Use AI to extract flight information from raw HTML.
    Used as fallback when traditional scraping fails.
    """
    import json
    import re
    
    # Truncate HTML to avoid token limits (keep first 30k chars usually enough for top results)
    # Better approach would be to only keep body text or specific containers
    truncated_html = html_content[:30000]
    
    prompt = f"""
    You are an expert web scraper. Extract flight information from the following HTML snippet.
    The page contains domestic Japan flights from {origin} to {dest} on {date}.
    
    HTML Content:
    ```html
    {truncated_html}
    ... (truncated)
    ```
    
    Task:
    Identify flight results in the HTML. For each flight, extract:
    1. Flight Number (e.g., ANA123, JL456)
    2. Departure Time (HH:MM)
    3. Arrival Time (HH:MM)
    4. Price (in JPY, just the number)
    5. Airline Code (e.g., NH for ANA, JL for JAL)
    
    Output Format:
    Return ONLY a valid JSON array of objects. No markdown formatting, no explanations.
    Example:
    [
      {{
        "airline": "NH",
        "flight_number": "123",
        "departure_time": "10:00",
        "arrival_time": "11:30",
        "price": 15000,
        "origin": "{origin}",
        "destination": "{dest}", 
        "date": "{date}",
        "id": "AI_EXTRACTED_1"
      }}
    ]
    
    If no flights are found, return empty array [].
    """
    
    provider = settings.AI_PROVIDER.lower()
    
    try:
        response_dict = {}
        if provider == "openai":
            response_dict = explain_with_openai(prompt)
        else:
            response_dict = explain_with_gemini(prompt)
            
        text = response_dict.get('text', '').strip()
        
        # Clean up code blocks if present
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        flights = json.loads(text)
        
        # Validate data structure
        valid_flights = []
        for idx, f in enumerate(flights):
            if all(k in f for k in ['flight_number', 'departure_time', 'arrival_time', 'price']):
                # Ensure fields are added
                f['origin'] = origin
                f['destination'] = dest
                f['date'] = date
                f['id'] = f"AI_{idx}_{f['flight_number']}"
                valid_flights.append(f)
                
        logger.info(f"AI extracted {len(valid_flights)} flights from HTML")
        return valid_flights
        
    except Exception as e:
        logger.error(f"AI HTML Extraction Error: {e}")
        return []

def generate_json_selector_fix(html_content: str, extracted_data: list[dict]) -> dict:
    """
    Ask AI to analyze the HTML and suggest new CSS selectors in JSON format.
    """
    import json
    
    truncated_html = html_content[:30000]
    sample_data = str(extracted_data[:2])
    
    prompt = f"""
    You represent a Self-Healing Code System.
    The web scraper's CSS selectors failed, but an AI fallback successfully extracted data.
    
    Your task: Reverse-engineer the CORRECT Playwright CSS selectors based on the HTML and Extracted Data.
    
    HTML Context:
    ```html
    {truncated_html}
    ...
    ```
    
    Target Data:
    {sample_data}
    
    Output Format:
    Return ONLY a valid JSON object with the following keys. No markdown, no code blocks.
    {{
      "container": "CSS selector for the list item (e.g. li.flight-row)",
      "flight_number": "CSS selector relative to container for flight number",
      "departure_time": "CSS selector relative to container for dep time",
      "arrival_time": "CSS selector relative to container for arr time",
      "price": "CSS selector relative to container for price"
    }}
    """
    
    provider = settings.AI_PROVIDER.lower()
    
    try:
        response_dict = {}
        if provider == "openai":
            response_dict = explain_with_openai(prompt)
        else:
            response_dict = explain_with_gemini(prompt)
            
        text = response_dict.get('text', '').strip()
        # Clean markdown
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"AI JSON Selector Generation Error: {e}")
        return None
