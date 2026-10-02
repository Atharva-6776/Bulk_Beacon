"""Day 1 data-quality test.

Runs real SerpApi queries for each candidate category in your city, saves every
response as a fixture, and prints a quality report so the team can pick the 3
categories with the best data.

Usage:
  python scripts/day1_test.py --city Pune
  python scripts/day1_test.py --city Pune --profiles tomatoes cement --deep
Credits: about 4 per profile (1 Maps, 1 marketplace, 1 Shopping, 1 transport);
--deep runs every Maps query for the profile.
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bulkbeacon.normalizer import (dedupe, maps_to_suppliers,
                                   marketplace_to_suppliers, shopping_to_suppliers)
from bulkbeacon.profiles import load_profiles
from bulkbeacon.serpapi_client import SerpApiClient

REPORT = Path(__file__).resolve().parent.parent / "fixtures" / "day1_report.md"


def pct(n, d):
    return f"{round(100 * n / d)}%" if d else "n/a"


def analyse_profile(client, p, city, deep):
    lines, stats = [], {}
    maps_queries = p["maps_queries"] if deep else p["maps_queries"][:1]
    maps = []
    for q in maps_queries:
        data = client.search(engine="google_maps", type="search", q=q.format(city=city))
        maps += maps_to_suppliers(data)
    maps = dedupe(maps)
    n = len(maps)
    stats["maps"] = n
    stats["phone_pct"] = (sum(1 for s in maps if s.phone) / n) if n else 0
    reviews = [s.review_count for s in maps]
    lines.append(f"### {p['name']} (`{p['id']}`)")
    lines.append(f"- Maps: **{n}** unique places | phone {pct(sum(1 for s in maps if s.phone), n)} | "
                 f"website {pct(sum(1 for s in maps if s.website), n)} | "
                 f"median reviews {statistics.median(reviews) if reviews else 'n/a'}")
    for s in maps[:5]:
        lines.append(f"  - {s.name} ({s.category or 'type n/a'}), rating {s.rating}, {s.review_count} reviews")

    mk = marketplace_to_suppliers(client.search(
        engine="google", q=f"site:{p['marketplace_domain']} " + p["marketplace_queries"][0].format(city=city),
        location=f"{city}, India"), p["marketplace_domain"])
    stats["market"] = len(mk)
    lines.append(f"- Marketplace ({p['marketplace_domain']}): **{len(mk)}** listings")
    for s in mk[:3]:
        lines.append(f"  - {s.name}")

    shop = shopping_to_suppliers(client.search(engine="google_shopping", q=p["shopping_query"],
                                               location=f"{city}, India"))
    prices = [s.unit_price for s in shop if s.unit_price]
    stats["shop_prices"] = len(prices)
    lines.append(f"- Shopping: **{len(shop)}** results, {len(prices)} with price" +
                 (f" (min {min(prices)}, median {statistics.median(prices)}, max {max(prices)})" if prices else ""))

    tr = maps_to_suppliers(client.search(engine="google_maps", type="search",
                                         q=p["logistics_query"].format(city=city)))
    stats["transport"] = len(tr)
    lines.append(f"- Transport (Maps): **{len(tr)}** providers")

    # Rough heuristic, thresholds are our own assumptions; read the lists above yourself.
    score = (n >= 8) + (stats["phone_pct"] >= 0.6) + (len(mk) >= 3) + (len(tr) >= 5) + (len(prices) >= 3)
    stats["score"] = score
    lines.append(f"- Heuristic data score: **{score}/5** (always eyeball the names above for relevance)\n")
    return lines, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True)
    ap.add_argument("--profiles", nargs="*", help="profile ids; default = all")
    ap.add_argument("--deep", action="store_true", help="run all Maps queries per profile")
    a = ap.parse_args()

    client = SerpApiClient()
    profiles = load_profiles(a.profiles)
    report, ranking = [f"# Day 1 data report: {a.city}\n"], []
    for pid, p in profiles.items():
        print(f"Testing {pid} ...")
        try:
            lines, stats = analyse_profile(client, p, a.city, a.deep)
        except Exception as e:  # keep going so one failure doesn't waste credits already spent
            print(f"  failed: {type(e).__name__}: {e}")
            report.append(f"### {pid}\n- FAILED: {type(e).__name__}: {e}\n")
            continue
        report += lines
        ranking.append((stats["score"], pid))

    ranking.sort(reverse=True)
    report.append("## Ranking by heuristic score\n" + "\n".join(f"{i+1}. {pid} ({sc}/5)" for i, (sc, pid) in enumerate(ranking)))
    text = "\n".join(report)
    REPORT.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"\nReal SerpApi calls this run: {client.network_calls} | cache hits: {client.cache_hits} | "
          f"calls made from this machine this month: {client.credits_used_this_month()}")
    print(f"Report saved to {REPORT}")


if __name__ == "__main__":
    main()
