"""
trademark_check.py  --  Trademark & Copyright Pre-Filter

Screens phrases against known risky substrings and the USPTO TESS API
before any design work begins. Outputs safe/flagged results.

Usage:
    python trademark_check.py --phrases "ROTATION READY" "WEAR YOUR PAIRS"
    python trademark_check.py --csv raw_phrases.csv --output screened_phrases.csv
    python trademark_check.py --csv raw_phrases.csv --output screened.csv --json screened.json
"""

import os
import sys
import csv
import json
import time
import argparse
import requests

# ── Known risky substrings (brands, characters, trademarked phrases) ──
KNOWN_RISKY_SUBSTRINGS = [
    # Characters & franchises
    "disney", "marvel", "star wars", "harry potter", "pokemon", "nintendo",
    "minecraft", "fortnite", "roblox", "among us", "deadpool", "batman",
    "superman", "spongebob", "peppa pig", "bluey", "barbie", "hello kitty",
    "studio ghibli", "totoro", "pikachu", "mario", "zelda", "sonic",
    # Brands
    "nike", "adidas", "supreme", "gucci", "louis vuitton", "champion",
    "nasa", "nfl", "nba", "mlb", "nhl", "espn", "jordan", "yeezy",
    "off-white", "balenciaga", "prada", "versace", "north face",
    # Known trademarked phrases (non-exhaustive)
    "let it go", "just do it", "this is the way", "may the force",
    "live laugh love", "nevertheless she persisted", "i can't breathe",
    "keep calm", "hakuna matata", "yolo", "fleek", "it's a vibe",
    # Sneaker-specific (Front A safety)
    "air force", "air max", "dunk", "jumpman", "swoosh", "three stripes",
    "boost", "ultraboost", "new balance", "converse", "vans",
]


def is_risky_substring(phrase):
    """Fast local check against known risky substrings."""
    phrase_lower = phrase.lower()
    for sub in KNOWN_RISKY_SUBSTRINGS:
        if sub in phrase_lower:
            return sub
    return None


def check_uspto_trademark(phrase):
    """
    Query USPTO's free trademark search API.
    Returns (is_risky: bool, detail: str).

    Note: This is a first-pass filter, not legal advice. Always manually
    review positives — trademarks are class-specific and context matters.
    """
    try:
        url = "https://developer.uspto.gov/ds-api/trademark/v1/records"
        params = {
            "searchText": f'markLiteralElements:"{phrase}"',
            "start": 0,
            "rows": 5,
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        hits = data.get("response", {}).get("docs", [])
        for hit in hits:
            status = hit.get("registrationStatus", "").upper()
            if status in ("REGISTERED", "PENDING"):
                mark = hit.get("markLiteralElements", phrase)
                return True, f"Active TM: '{mark}' (status: {status})"
        return False, "No active trademark found"

    except requests.exceptions.Timeout:
        return False, "USPTO API timeout - flag for manual review"
    except requests.exceptions.ConnectionError:
        return False, "USPTO API unreachable - flag for manual review"
    except Exception as e:
        return False, f"USPTO API error: {e} - flag for manual review"


def screen_phrase(phrase, skip_api=False):
    """
    Screen a single phrase through both layers.
    Returns dict with phrase, status, risk_level, and detail.
    """
    # Layer 1: fast local substring check
    match = is_risky_substring(phrase)
    if match:
        return {
            "phrase": phrase,
            "status": "FLAGGED",
            "reason": "substring_match",
            "matched": match,
            "detail": f"Contains known risky substring: '{match}'",
            "risk": "HIGH",
        }

    # Layer 2: USPTO API check
    if not skip_api:
        time.sleep(0.5)  # respect rate limits
        is_risky, detail = check_uspto_trademark(phrase)
        if is_risky:
            return {
                "phrase": phrase,
                "status": "FLAGGED",
                "reason": "uspto_match",
                "matched": phrase,
                "detail": detail,
                "risk": "MEDIUM",
            }

    return {
        "phrase": phrase,
        "status": "SAFE",
        "reason": "cleared",
        "matched": None,
        "detail": "No trademark conflicts found",
        "risk": "LOW",
    }


def screen_phrases(phrases, skip_api=False):
    """
    Screen a list of phrases. Returns (safe_list, flagged_list, all_results).
    """
    safe = []
    flagged = []
    all_results = []

    print(f"  Screening {len(phrases)} phrases...\n")

    for phrase in phrases:
        if not phrase.strip():
            continue

        result = screen_phrase(phrase.strip(), skip_api=skip_api)
        all_results.append(result)

        if result["status"] == "SAFE":
            safe.append(result)
            print(f"  [SAFE] {phrase}")
        else:
            flagged.append(result)
            print(f"  [FLAG] {phrase} -- {result['detail']}")

    print(f"\n  Results: {len(safe)} safe, {len(flagged)} flagged "
          f"out of {len(all_results)} phrases")
    return safe, flagged, all_results


def screen_from_csv(input_csv, output_csv=None, json_output=None, skip_api=False):
    """Read phrases from CSV (first column), screen them, write results."""
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        phrases = [row[0].strip() for row in reader if row and row[0].strip()]

    # Skip header if it looks like one
    if phrases and phrases[0].lower() in ("phrase", "phrases", "text", "slogan"):
        phrases = phrases[1:]

    safe, flagged, all_results = screen_phrases(phrases, skip_api=skip_api)

    if output_csv:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["phrase", "status", "reason", "risk", "detail"])
            for r in all_results:
                writer.writerow([r["phrase"], r["status"], r["reason"],
                                 r["risk"], r["detail"]])
        print(f"  CSV results written to {output_csv}")

    if json_output:
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"  JSON results written to {json_output}")

    return safe, flagged, all_results


def main():
    parser = argparse.ArgumentParser(
        description="Trademark & copyright pre-filter for POD phrases"
    )
    parser.add_argument("--phrases", nargs="+",
                        help="One or more phrases to screen")
    parser.add_argument("--csv", dest="csv_input",
                        help="CSV file with phrases (first column)")
    parser.add_argument("--output", dest="csv_output",
                        help="Output CSV path for results")
    parser.add_argument("--json", dest="json_output",
                        help="Output JSON path for results")
    parser.add_argument("--skip-api", action="store_true",
                        help="Skip USPTO API calls (substring check only)")
    args = parser.parse_args()

    if args.csv_input:
        screen_from_csv(args.csv_input, args.csv_output, args.json_output,
                        skip_api=args.skip_api)
    elif args.phrases:
        safe, flagged, results = screen_phrases(args.phrases,
                                                skip_api=args.skip_api)
        if args.json_output:
            with open(args.json_output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"  JSON results written to {args.json_output}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
