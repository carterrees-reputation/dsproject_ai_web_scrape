import os, json, time, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info

load_dotenv()

target_url        = "https://www.autonation.com/cars-for-sale?mk=chrysler"
output_html_path  = "outputs/autonation_rendered.html"
output_json_path  = "outputs/autonation_results.json"
projection_sizes  = [100, 1_000, 100_000, 1_000_000]

graph_config = {
    "llm": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model":   "openai/gpt-4o-mini",
    },
    "verbose":  True,
    "headless": False,
}

prompt = """
You are a smart web-scraping assistant. The HTML is from a car-listing site.

For every car extract:
- car_name
- car_status
- car_price
- car_mileage (⚠️ return the EXACT text shown on the page, including
               all digits, commas, and the word “miles”. Do not
               abbreviate or round.)

Return ONLY a JSON array of car objects. No markdown, no commentary.
"""

# ── Playwright render ────────────────────────────────────────────────────
def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page    = browser.new_page()
        page.goto(url, timeout=60_000)
        time.sleep(10)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)
        html = page.content()
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html)
        browser.close()
        print("✅ HTML rendered & saved.")
        return html
# ────────────────────────────────────────────────────────────────────────
html_content = fetch_rendered_html(target_url)

scraper = SmartScraperGraph(prompt=prompt, source=html_content, config=graph_config)
result  = scraper.run()

print("\n✅ Extracted JSON:")
print(json.dumps(result, indent=4))

os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4)

# ── Execution info & cost extraction ─────────────────────────────────────
exec_info_list = scraper.execution_info          # list[dict]
print("\n📊 Execution Info:")
print(prettify_exec_info(exec_info_list))

def extract_node_cost(node: dict) -> float:
    """
    Each node dict has a key that contains 'cost' (e.g. 'Cost ($)').
    Convert it safely to float, stripping a leading '$' if present.
    """
    for k, v in node.items():
        if "cost" in k.lower():
            try:
                return float(str(v).replace("$", "").strip())
            except ValueError:
                return 0.0
    return 0.0

total_cost = sum(extract_node_cost(node) for node in exec_info_list)

# cars scraped this run
cars = result if isinstance(result, list) else result.get("content", [])
cars_in_run = len(cars)

# ── Projections ──────────────────────────────────────────────────────────
if cars_in_run and total_cost:
    cost_per_car = total_cost / cars_in_run
    print(f"\nRun summary • Cars: {cars_in_run} • Cost: ${total_cost:.4f} "
          f"• Cost/car: ${cost_per_car:.6f}\n")
    for qty in projection_sizes:
        print(f"   ▸ Estimated cost for {qty:>9,} cars :  "
              f"${qty * cost_per_car:,.2f}")
else:
    print("\n⚠️ Unable to project cost (zero cars or zero cost detected).")
