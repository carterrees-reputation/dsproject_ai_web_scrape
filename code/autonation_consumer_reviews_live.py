import os, json, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info

"""
This script scrapes customer reviews for AutoNation from the ConsumerAffairs website.

It performs the following steps:
1.  Uses Playwright to fully render the webpage, clicking "Load more" until all
    reviews are visible on the page, and saves the final HTML content.
2.  Uses ScrapeGraphAI with an OpenAI LLM (gpt-4o-mini) to parse the saved HTML.
3.  Instructs the LLM to extract specific fields for each review (name, location,
    date, rating, tags, text, derived likes/dislikes) into a structured JSON format.
4.  Saves the extracted review data as a JSON file.
5.  Prints a preview of the first two extracted reviews.
6.  Calculates the cost of the ScrapeGraphAI run based on token usage reported
    in the execution info.
7.  Projects the estimated cost for scraping larger numbers of reviews based on
    the calculated cost per review.
"""

# ─────────────────── Environment Variables / File Paths / Constants ───────────────────
load_dotenv()  # Load environment variables from a .env file (e.g., OPENAI_API_KEY)

# Define the absolute path for the output directory
OUTPUT_DIR = "/Users/crees/PycharmProjects/dsproject_web_scrape/outputs"

# The target URL on ConsumerAffairs containing AutoNation reviews.
URL = "https://www.consumeraffairs.com/automotive/autonation.htm"
# Path where the fully rendered HTML content will be saved.
OUT_HTML = os.path.join(OUTPUT_DIR, "ca_autonation_rendered.html")
# Path where the extracted review data (JSON) will be saved.
OUT_JSON = os.path.join(OUTPUT_DIR, "ca_autonation_reviews.json")

# List of review quantities for cost projection calculations.
PROJECTIONS = [100, 1_000, 100_000, 1_000_000]

# ── Playwright: Render Full Page with All Reviews ───────────────────────────────────
def render_full_page(url: str) -> str:
	"""
    Uses Playwright to navigate to a URL, repeatedly click the "Load more" button
    until it disappears, ensuring all dynamic content (reviews) is loaded.
    Saves the final HTML content to a file and returns the HTML string.

    Args:
        url (str): The URL of the page to render.

    Returns:
        str: The fully rendered HTML content of the page.

    Side Effects:
        - Creates the output directory if it doesn't exist.
        - Writes the rendered HTML to the file specified by OUT_HTML.
    """
	print(f"Starting Playwright to render: {url}")
	with sync_playwright() as p:
		# Launch Chromium browser. headless=False shows the browser window.
		browser = p.chromium.launch(headless=False)
		page = browser.new_page(
			# Set a common user agent to mimic a real browser.
			user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
			            "AppleWebKit/537.36 (KHTML, like Gecko) "
			            "Chrome/119.0.0.0 Safari/537.36")
		)
		# Navigate to the URL, increasing the default timeout.
		page.goto(url, timeout=60_000)
		print("Page loaded. Searching for 'Load more' button...")

		# Loop to click the "Load more" button until it's no longer found.
		while True:
			load_more = page.query_selector('button:has-text("Load more")')
			if not load_more:
				print("'Load more' button not found. Assuming all reviews are loaded.")
				break  # Exit the loop if the button doesn't exist.

			print("Clicking 'Load more'...")
			load_more.click()
			# Wait briefly for new content to potentially load after the click.
			page.wait_for_timeout(1500)
			# Scroll down to potentially trigger lazy-loading or ensure button visibility.
			page.keyboard.press("End")

		# Final scroll down after the loop finishes.
		page.keyboard.press("End")
		time.sleep(1)  # Short pause to allow final rendering.

		# Get the complete HTML content of the page.
		html = page.content()
		# Ensure the output directory exists.
		os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
		# Save the HTML content to the specified file.
		with open(OUT_HTML, "w", encoding="utf-8") as f:
			f.write(html)
		# Close the browser instance.
		browser.close()
		print(f"All reviews loaded and HTML saved → {OUT_HTML}")
		return html


# ─────────────────── SmartScraperGraph Configuration ────────────────────────────────
# Configuration for the ScrapeGraphAI graph.
graph_cfg = {
	"llm": {
		# Use the OpenAI API key from environment variables.
		"api_key": os.getenv("OPENAI_API_KEY"),
		# Specify the OpenAI model to use for extraction.
		"model": "openai/gpt-4o-mini",
	},
	# Enable verbose logging to see ScrapeGraphAI's internal steps.
	"verbose": True,
	# Set headless mode for the internal browser used by ScrapeGraphAI (if any).
	# Note: This is separate from the Playwright rendering done earlier.
	"headless": False,
}

# The detailed prompt instructing the LLM on how to extract review data.
PROMPT = """
You are a smart web-scraping assistant tasked with extracting customer review data.
The provided HTML source contains multiple customer reviews about AutoNation from ConsumerAffairs.

Your goal is to identify each individual review and extract the following fields precisely:
- reviewer_name: The name of the person who wrote the review.
- reviewer_location: The city and state (or country) of the reviewer, if available.
- review_date: The date the review was posted (extract only the date part, e.g., "YYYY-MM-DD" or "Month Day, Year").
- star_rating: The numerical star rating given by the reviewer (integer from 1 to 5).
- tags: A list of strings representing the short descriptive tags associated with the review 
(often shown as grey chips/pills). If none, use an empty list [].
- review_text: The full text content of the customer's review paragraph.
- likes: A list of strings containing up to 3 very brief positive points or phrases mentioned by the reviewer. Infer 
    these from the review_text. If the review is mostly negative or neutral, or no specific positive points are mentioned, 
    use an empty list [].
- dislikes: A list of strings containing up to 3 very brief negative points or phrases mentioned by the reviewer. Infer 
    these from the review_text. If the review is mostly positive or neutral, or no specific negative points are mentioned, 
    use an empty list [].

Guidelines for deriving 'likes' and 'dislikes':
- Consider the 'star_rating':
    - 4 or 5 stars: Focus primarily on extracting 'likes'. 'Dislikes' should likely be empty unless explicitly negative points are made.
    - 1 or 2 stars: Focus primarily on extracting 'dislikes'. 'Likes' should likely be empty unless explicitly positive points are made.
    - 3 stars: Both 'likes' and 'dislikes' might be present; extract relevant brief phrases for both if applicable.
- Keep the phrases very short and directly related to the review content.

Output Format:
Return ONLY a valid JSON array where each element is an object representing a single review, containing exactly the keys specified above.
Do NOT include any introductory text, markdown formatting (like ```json ... ```), or any keys not listed in the requirements.
Example of one review object in the array:
{
  "reviewer_name": "Jane D.",
  "reviewer_location": "Anytown, CA",
  "review_date": "2023-10-26",
  "star_rating": 5,
  "tags": ["Customer Service", "Easy Process"],
  "review_text": "The entire process was smooth and the staff were very helpful...",
  "likes": ["Smooth process", "Helpful staff"],
  "dislikes": ["Sales person had bad breath."]
}
"""

# ─────────────────── Run the Scraper ───────────────────────────────────────────────
# Step 1: Render the full page using Playwright to get the complete HTML.
html_content = render_full_page(URL)

# Step 2: Initialize the SmartScraperGraph with the prompt, HTML source, and config.
# The source is the HTML string obtained from Playwright.
scraper = SmartScraperGraph(
	prompt=PROMPT,
	source=html_content,  # Use the rendered HTML, not the URL
	config=graph_cfg
)

# Step 3: Run the scraping process. ScrapeGraphAI handles the LLM call and parsing.
# The result should ideally be the Python list of review dictionaries directly.
print("Starting ScrapeGraphAI extraction...")
reviews_data = scraper.run()
print("ScrapeGraphAI finished.")

# ─────────────────── Save Extracted Data to JSON & Preview ────────────────────────
# Ensure the output directory exists.
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

# Save the extracted reviews data to the specified JSON file.
with open(OUT_JSON, "w", encoding="utf-8") as f:
	# Use json.dump for pretty printing with indentation.
	json.dump(reviews_data, f, indent=4)
	print(f"Saved extracted reviews JSON → {OUT_JSON}")

# Print the first two extracted reviews for a quick sanity check.
print("\nPreview of first 2 extracted reviews:")
# Check if the result is a list (expected) or potentially a dict (fallback).
if isinstance(reviews_data, list):
	# If it's a list, print the first 2 items.
	print(json.dumps(reviews_data[:2], indent=2))
elif isinstance(reviews_data, dict) and "content" in reviews_data:
	# If it's a dict with a 'content' key (sometimes happens), print from there.
	print(json.dumps(reviews_data.get("content", [])[:2], indent=2))
else:
	# If the structure is unexpected, print a message.
	print("Unexpected data structure returned by scraper. Cannot preview.")
	print(f"Raw data type: {type(reviews_data)}")

# ─────────────────── Cost Calculation and Projections ─────────────────────────────
# Retrieve the execution information which contains cost details per node.
exec_info = scraper.execution_info


def _to_float(x) -> float:
	"""
    Safely converts various input types (int, float, cost strings like '$0.123')
    into a float value. Returns 0.0 if conversion is not possible.

    Args:
        x: The value to convert (can be int, float, str, or other).

    Returns:
        float: The converted float value, or 0.0 on failure.
    """
	if isinstance(x, (int, float)):
		return float(x)
	if isinstance(x, str):
		# Attempt to remove '$' and whitespace before converting.
		try:
			return float(x.replace("$", "").strip())
		except ValueError:
			return 0.0  # Return 0 if string conversion fails
	return 0.0  # Return 0 for any other types


# Calculate the total cost by summing up cost values from the execution info.
total_cost = sum(
	_to_float(v)  # Use the safe conversion function
	for node_info in exec_info  # Iterate through each node's execution details
	for k, v in node_info.items()  # Iterate through key-value pairs in the node info
	if "cost" in k.lower()  # Check if the key contains 'cost' (case-insensitive)
)

# Determine the number of successfully extracted reviews.
# Handle both list and dict return types from the scraper.
review_list = []
if isinstance(reviews_data, list):
	review_list = reviews_data
elif isinstance(reviews_data, dict):
	review_list = reviews_data.get("content", [])  # Safely get 'content' or empty list

n_reviews = len(review_list)

# Print the detailed execution information (timing, costs per node).
print("Execution Info:")
print(prettify_exec_info(exec_info))

# Calculate and print cost summary and projections if possible.
if n_reviews > 0 and total_cost > 0:
	# Calculate the average cost per extracted review.
	cost_per_review = total_cost / n_reviews
	print(f"\nRun summary • Reviews scraped: {n_reviews} "
	      f"• Total Cost: ${total_cost:.4f} • Cost/review: ${cost_per_review:.6f}\n")
	# Print cost projections for different quantities of reviews.
	print("Cost Projections:")
	for quantity in PROJECTIONS:
		projected_cost = quantity * cost_per_review
		# Format numbers for readability (commas for thousands, 2 decimal places for cost).
		print(f" ▸ Estimated cost for {quantity:>9,} reviews :  ${projected_cost:,.2f}")
else:
	# Print a warning if cost calculation isn't possible.
	print("Unable to project cost (zero reviews extracted or zero cost reported).")
