# BulkBeacon

Need it in bulk, today? Find suppliers, send quote requests, compare quotes.
Built for the SerpApi India Hackathon 2026 (deadline 10 Oct 2026, 23:59 IST).

> Status: Scaffold + Core Refactor. Implemented: Generic product-agnostic pipeline, SerpApi client (cache, call cap, demo mode),
> shared schemas, normalizer, category profiles with dynamic LLM generation fallback, Day 1 data test. Not yet built:
> trust scorer, ranker, API, frontend, quote comparison (see SRS). See `ARCHITECTURE.md` for details.

## Setup
```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env, then add your SERPAPI_KEY
python -m unittest discover -s tests -v
```

## Day 1: test which categories have good data in your city
```
python scripts/day1_test.py --city Pune
```
- Costs about 4 SerpApi credits per profile (6 profiles = ~24). Free plan = 250/month.
- Every response is saved to `fixtures/cache/`, so re-running is free. **Commit these
  fixtures** so teammates and demo mode can reuse them (they contain no API key).
- Read `fixtures/day1_report.md`. The 5-point score is only a rough heuristic;
  check that the supplier names are actually relevant to the category.
- Keep the 3 best categories, then set `"validated": true` in their profile files.

## Rules for the team
1. Never commit `.env` or any key.
2. Never call `requests` for SerpApi directly; always use `SerpApiClient` (cache + cap).
3. Build against `bulkbeacon/schemas.py`; change it only after telling everyone.
4. Work on branches; no direct pushes to `main`.
5. `BULKBEACON_DEMO=1` runs from fixtures only (no key, no network).

## Layout
```
bulkbeacon/serpapi_client.py   cached client, call cap, demo mode
bulkbeacon/schemas.py          Supplier / Request contract
bulkbeacon/normalizer.py       Maps / Search / Shopping -> Supplier, dedupe
bulkbeacon/profiles.py         loads profiles/*.json
profiles/                      6 candidate category profiles (unvalidated)
scripts/day1_test.py           data-quality test + report
tests/                         offline unit tests
```

## Limitations (also shown in the app)
Search data cannot give real wholesale prices, verify stock or quality, or prove a
supplier is genuine. Retail prices are benchmarks only; trust scores are risk signals.
