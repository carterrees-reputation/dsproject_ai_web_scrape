import os
import json
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info

# Load .env environment variables
load_dotenv()

# Set the target URL
target_url = "https://www.autonation.com/cars-for-sale?mk=chrysler"

# Function to fetch fully rendered HTML with Playwright
def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        page = context.new_page()
        page.goto(url, timeout=60000)

        try:
            page.wait_for_selector("ansrp-srp-tile-v3", timeout=30000)
            print("✅ Car tiles loaded.")
        except Exception as e:
            print("⚠️ Timeout waiting for car tiles.")
            raise e

        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)  # Let lazy-loaded content hydrate

        html = page.content()
        browser.close()
        return html

# Fetch rendered HTML from the live webpage
rendered_html = fetch_rendered_html(target_url)

# Configuration for GPT-4o-mini
graph_config = {
    "llm": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "openai/gpt-4o-mini",
    },
    "verbose": True,
    "headless": False,
}

# Web scraping prompt tailored to AutoNation's car tile structure
prompt = """
You are a smart web scraping assistant. The HTML describes a list of cars from AutoNation.

Each car listing is inside a <ansrp-srp-tile-v3> tag.

Extract the following:

- **car_name**: From the <h3> tag inside `.tile-info`, including nested <span>.
- **car_status**: From the <span class="tile-status"> element (e.g., "In Stock").
- **car_price**: From <div class="price-Value">. If missing, return "N/A".
- **car_mileage**: From the <span class="vehicle-mileage"> element. Trim whitespace.

Only return a JSON array like:
[
  {
    "car_name": "2023 Acura Integra CVT w/A-Spec Technology Package",
    "car_status": "In Stock",
    "car_price": "$27,584",
    "car_mileage": "9 miles"
  }
]
Only JSON. No explanation or markdown.
"""


# Run SmartScraperGraph with rendered HTML
smart_scraper_graph = SmartScraperGraph(
    prompt=prompt,
    source=rendered_html,
    config=graph_config
)

# Execute the scraping pipeline
result = smart_scraper_graph.run()
print("✅ Extracted JSON result:")
print(json.dumps(result, indent=4))

# Execution stats
print("\n📊 Execution Info:")
print(prettify_exec_info(smart_scraper_graph.get_execution_info()))
