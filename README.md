# dsproject_ai_web_scrape

## Overview

This project is designed to perform web scraping using AI to extract data from various web pages. It leverages Playwright for rendering web pages and ScrapeGraphAI for parsing and extracting structured data using OpenAI's language models.

## Project Structure

- **autonation_consumer_reviews_live.py**: Scrapes customer reviews for AutoNation from the ConsumerAffairs website. It uses Playwright to render the page and ScrapeGraphAI to extract review data into a structured JSON format.
- **autonation_live_scrape_minimal.py**: A minimal script to scrape car listings from AutoNation's website. It extracts car details such as name, status, price, and mileage.
- **autonation_live_scrape.py**: Similar to the minimal version but includes additional configurations and error handling for scraping car listings.
- **scrape_scrapegraphai_site_static.py**: Loads pre-rendered HTML content from a file and uses ScrapeGraphAI to extract car details.

## Setup

1. **Environment Variables**: Ensure you have a `.env` file with the necessary API keys, such as `OPENAI_API_KEY`.
2. **Dependencies**: Install the required packages using `npm install` or `pip install` for Python dependencies.

## Usage

- Run the scripts using Python to scrape data from the specified URLs.
- The extracted data will be saved in the `outputs` directory in JSON format.

## Features

- **Dynamic Content Rendering**: Uses Playwright to render dynamic web pages fully.
- **AI-Powered Data Extraction**: Utilizes OpenAI's models to parse and extract structured data.
- **Cost Estimation**: Projects the cost of scraping based on token usage.

## License

This project is licensed under the MIT License. 