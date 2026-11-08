#!/usr/bin/env python3
"""
Google Custom Search JSON API Client for Deals, Products, Sialkot Food & Expanded Clothing Brands with Date Validation
"""

import sys
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException

API_KEY = "AIzaSyD5HX2UndQllmtxzEsSeQXZ8b2BKz2HdlY"
SEARCH_ENGINE_ID = "77acdf39a5965495b"
API_URL = "https://www.googleapis.com/customsearch/v1"

# Curated queries including Sialkot Local Food Points & Expanded Clothing Brands
CURATED_QUERIES = [
    "HFC Sialkot food deals discounts",
    "Ranchers Sialkot burgers offers",
    "Frangoes Sialkot fried chicken discount",
    "Mei Kong Sialkot restaurant deals",
    "Narkins Shalwar Kameez Blessed Friday sale",
    "edenrobe winter collection discount",
    "Limelight lawn collection sale",
    "Ideas Gul Ahmed blessed friday sale",
    "Alkaram studio clearance discount",
    "Bata service shoes footwear clearance"
]

def is_valid_deal_date(pub_date_str: str) -> bool:
    """
    Validates if a deal announcement is within the current valid date range (e.g. not expired).
    Returns True if valid or if date cannot be parsed (to avoid false negatives).
    """
    if not pub_date_str:
        return True
    try:
        # Simple heuristic check for expired dates or seasonal tags
        current_date = datetime.now()
        # If date string mentions a past year or expired period
        if str(current_date.year - 1) in pub_date_str:
            return False
        return True
    except Exception:
        return True

def search_deals(query: str, num_results: int = 10) -> list:
    """
    Searches for deals and products using Google Custom Search API with date validation & deduplication.
    """
    params = {
        'key': API_KEY,
        'cx': SEARCH_ENGINE_ID,
        'q': query,
        'num': min(max(1, num_results), 10)
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)

        if response.status_code == 429:
            print("[ERROR] API Quota limit exceeded or too many requests.", file=sys.stderr)
            return []
        elif response.status_code == 403:
            print("[ERROR] Invalid API key or unauthorized access.", file=sys.stderr)
            return []

        response.raise_for_status()
        data = response.json()

        items = data.get('items', [])
        formatted_results = []

        for item in items:
            title = item.get('title', 'No Title')
            snippet = item.get('snippet', 'No Description Available')
            link = item.get('link', '')

            # Date validation check
            if not is_valid_deal_date(snippet):
                continue

            # Extract Image URL from pagemap if available
            image_url = None
            pagemap = item.get('pagemap', {})

            if 'cse_image' in pagemap and len(pagemap['cse_image']) > 0:
                image_url = pagemap['cse_image'][0].get('src')
            elif 'cse_thumbnail' in pagemap and len(pagemap['cse_thumbnail']) > 0:
                image_url = pagemap['cse_thumbnail'][0].get('src')
            elif 'metatags' in pagemap and len(pagemap['metatags']) > 0:
                image_url = pagemap['metatags'][0].get('og:image')

            formatted_results.append({
                'title': title,
                'snippet': snippet,
                'link': link,
                'image_url': image_url or 'N/A'
            })

        # Strict Deduplication
        seen = set()
        unique_results = []
        for res in formatted_results:
            identifier = (res['title'], res['link'])
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(res)

        return unique_results

    except RequestException as e:
        print(f"[ERROR] Network request failed: {e}", file=sys.stderr)
        return []
    except ValueError as e:
        print(f"[ERROR] Failed to parse JSON response: {e}", file=sys.stderr)
        return []

def main():
    print("=== Google Custom Search Sialkot Food & Expanded Brand Deal Finder ===")
    print("Current Date/Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    query = input("Enter search query (or press Enter for curated Sialkot/Brand deals): ").strip()
    if not query:
        query = "HFC Sialkot Narkins edenrobe deals"

    print(f"\nSearching for '{query}'...")
    results = search_deals(query)

    if not results:
        print("No valid active results found or quota limit reached.")
        return

    print(f"\nFound {len(results)} valid active results:\n" + "="*50)
    for idx, res in enumerate(results, 1):
        print(f"[{idx}] {res['title']}")
        print(f"    Link: {res['link']}")
        print(f"    Image: {res['image_url']}")
        print(f"    Summary: {res['snippet']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
