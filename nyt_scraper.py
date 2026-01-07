"""
NYT Pips Puzzle Scraper

Fetches puzzle data from the NYT Games API.
Requires your NYT-S cookie value (from browser DevTools).

Usage:
  python nyt_scraper.py --cookie YOUR_NYT_S_COOKIE --date 2025-01-05

To get your NYT-S cookie:
1. Go to nytimes.com/games/pips in your browser
2. Open DevTools (F12) -> Application -> Cookies
3. Find the NYT-S cookie and copy its value
"""

import argparse
import json
import requests
from datetime import datetime, timedelta


def fetch_pips_puzzle(date_str: str, nyt_s_cookie: str) -> dict:
    """
    Fetch Pips puzzle data for a specific date.

    Tries several possible endpoint patterns based on NYT API conventions.
    """
    # Possible API endpoints (based on other NYT games patterns)
    endpoints = [
        f"https://www.nytimes.com/svc/games/pips/v2/{date_str}.json",
        f"https://www.nytimes.com/svc/pips/v2/{date_str}.json",
        f"https://www.nytimes.com/svc/games-hub/puzzle/pips/{date_str}.json",
        f"https://www.nytimes.com/games-assets/pips/{date_str}.json",
    ]

    headers = {
        'Cookie': f'NYT-S={nyt_s_cookie};',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    for endpoint in endpoints:
        try:
            print(f"Trying: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)

            if response.status_code == 200:
                print(f"  Success! Status: {response.status_code}")
                return response.json()
            else:
                print(f"  Status: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

    return None


def fetch_game_page(date_str: str, nyt_s_cookie: str) -> str:
    """
    Fetch the full game page HTML which may contain embedded puzzle data.
    """
    url = f"https://www.nytimes.com/games/pips?d={date_str}"

    headers = {
        'Cookie': f'NYT-S={nyt_s_cookie};',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    try:
        print(f"Fetching game page: {url}")
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            print(f"  Got {len(response.text)} characters")
            return response.text
        else:
            print(f"  Status: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return None


def extract_puzzle_from_html(html: str) -> dict:
    """
    Extract puzzle data from embedded JavaScript/JSON in the page.
    Look for common patterns like window.gameData, __NEXT_DATA__, etc.
    """
    import re

    # Common patterns for embedded game data
    patterns = [
        r'window\.gameData\s*=\s*(\{.*?\});',
        r'"puzzle"\s*:\s*(\{.*?\})',
        r'"pipsData"\s*:\s*(\{.*?\})',
        r'__NEXT_DATA__.*?"props":\s*(\{.*?\})\s*<',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                print(f"  Found data with pattern: {pattern[:30]}...")
                return data
            except json.JSONDecodeError:
                continue

    # Try to find any JSON-like structures with puzzle keywords
    puzzle_indicators = ['cells', 'regions', 'dominos', 'constraints', 'tiles']

    # Look for script tags with JSON
    script_match = re.findall(r'<script[^>]*>([^<]+)</script>', html)
    for script in script_match:
        if any(ind in script.lower() for ind in puzzle_indicators):
            # Try to extract JSON
            json_match = re.search(r'(\{[^}]+("cells"|"regions"|"dominos")[^}]+\})', script)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass

    return None


def convert_to_our_format(nyt_data: dict) -> dict:
    """
    Convert NYT puzzle format to our internal format.

    Expected NYT format (approximate):
    {
        "cells": [[0,0], [0,1], ...],
        "regions": [
            {"kind": "sum", "target": 7, "cells": [[0,0], [1,0]]},
            ...
        ],
        "dominos": {"5|5": 1, "2|6": 1, ...}
    }
    """
    # This will need adjustment based on actual NYT format
    our_format = {
        "cells": nyt_data.get("cells", []),
        "regions": [],
        "dominoes": [],
    }

    # Convert regions
    for region in nyt_data.get("regions", []):
        our_region = {
            "cells": region.get("cells", []),
            "constraint_type": region.get("kind", "sum"),
            "target_value": region.get("target"),
        }
        our_format["regions"].append(our_region)

    # Convert dominoes
    for domino_str, count in nyt_data.get("dominos", {}).items():
        parts = domino_str.split("|")
        if len(parts) == 2:
            for _ in range(count):
                our_format["dominoes"].append({
                    "low": int(parts[0]),
                    "high": int(parts[1])
                })

    return our_format


def main():
    parser = argparse.ArgumentParser(description='Fetch NYT Pips puzzles')
    parser.add_argument('--cookie', required=True, help='NYT-S cookie value')
    parser.add_argument('--date', default=None, help='Date in YYYY-MM-DD format (default: yesterday)')
    parser.add_argument('--output', default='puzzle.json', help='Output file')

    args = parser.parse_args()

    if args.date:
        date_str = args.date
    else:
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')

    print(f"\n=== NYT Pips Scraper ===")
    print(f"Date: {date_str}")
    print()

    # Try direct API first
    print("--- Trying Direct API ---")
    puzzle_data = fetch_pips_puzzle(date_str, args.cookie)

    if puzzle_data:
        print(f"\nSuccess! Saving to {args.output}")
        with open(args.output, 'w') as f:
            json.dump(puzzle_data, f, indent=2)
        print(json.dumps(puzzle_data, indent=2)[:500] + "...")
        return

    # Try page scraping
    print("\n--- Trying Page Scraping ---")
    html = fetch_game_page(date_str, args.cookie)

    if html:
        puzzle_data = extract_puzzle_from_html(html)
        if puzzle_data:
            print(f"\nExtracted puzzle data! Saving to {args.output}")
            with open(args.output, 'w') as f:
                json.dump(puzzle_data, f, indent=2)
            print(json.dumps(puzzle_data, indent=2)[:500] + "...")
            return

        # Save HTML for manual inspection
        with open('pips_page.html', 'w') as f:
            f.write(html)
        print("\nCouldn't extract puzzle data automatically.")
        print("Saved page HTML to pips_page.html for manual inspection.")
        print("Look for JSON in <script> tags or network requests.")

    print("\nFailed to fetch puzzle data.")
    print("\nAlternative approach:")
    print("1. Open browser DevTools -> Network tab")
    print("2. Go to nytimes.com/games/pips")
    print("3. Look for XHR requests returning JSON")
    print("4. Copy that JSON data here")


if __name__ == "__main__":
    main()
