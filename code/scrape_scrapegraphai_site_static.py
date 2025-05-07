import os
import json
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info

# Load environment variables
load_dotenv()

# Path to the rendered HTML file
html_file_path = "/Users/crees/PycharmProjects/dsproject_web_scrape/outputs/autonation_rendered.html"

# Load the HTML content
with open(html_file_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Config to use OpenAI GPT-4o-mini
graph_config = {
    "llm": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "openai/gpt-4o-mini",
    },
    "verbose": True,
    "headless": False,
}

# Prompt customized to your DOM structure
prompt = """
You are a smart web scraping assistant. The HTML describes a list of cars from AutoNation.

Each car listing is inside a <ansrp-srp-tile-v3> tag.

- car_name: Extract the full text of the <h3> tag inside .tile-info, including any nested <span>.
- car_status: Extract from <span class="tile-status"> (e.g., "In Stock").
- car_price: Extract from <div class="price-Value">. If missing, return "N/A".

Only return a JSON array like this:
[
  {
    "car_name": "2023 Acura Integra CVT w/A-Spec Technology Package",
    "car_status": "In Stock",
    "car_price": "$27,584"
  }
]
Only return valid JSON. No explanation, no markdown.
"""

# Run SmartScraperGraph with the HTML content
smart_scraper_graph = SmartScraperGraph(
    prompt=prompt,
    source=html_content,
    config=graph_config
)

# Run and print results
result = smart_scraper_graph.run()
print("✅ Extracted JSON result:")
print(json.dumps(result, indent=4))

# Print execution info
print("\n📊 Execution Info:")
print(prettify_exec_info(smart_scraper_graph.get_execution_info()))
