# Duo Radar v2

Updates the original Streamlit dashboard with a live pin map when the upstream feed provides coordinates, last-24-hour inventory observations, a trend chart, and Apple checkout links beside reported configurations.

## Update existing GitHub repository

Extract the ZIP. Copy **the contents** of `duo_radar_v2` (including hidden `.github`) into your existing `duo_web_dashboard` repository folder, replacing `app.py`, `requirements.txt`, and `README.md` and adding `inventory_core.py`, `collect.py`, `history.json`, and `.github/workflows/inventory-history.yml`.

From your repo folder:

```bash
git add .
git commit -m "Add inventory history, map, and checkout links"
git push
```

GitHub Actions > Collect public inventory observations > Run workflow starts the first collection. Scheduled runs occur roughly every 10 minutes (not guaranteed; GitHub may delay/skip runs). Ensure Actions is enabled and workflow has contents:write permission. Streamlit Cloud redeploys after pushes. It may sleep when unused.

## Important caveats

- The endpoint `https://pickupchecker.com/api/v1/us/stock?model=duo` is **unofficial and not live-verified**. If it rejects requests or returns a different schema, the dashboard reports an error rather than fabricated stock. Verify provider permission and rate limits before enabling automated public polling.
- **History begins after you enable the collector**. It cannot reconstruct past 24 hours from a current-stock endpoint. Each saved snapshot is an observation; first-seen timestamps are not necessarily restock times. A stale provider timestamp is rejected for collection.
- **Map pins only show locations for which the provider supplies coordinates.** If none are present, the app explains why instead of inventing positions.
- Checkout links go to the official Apple purchase page, not a preselected cart. Apple does not guarantee that a specific store's inventory is reserved by opening the link.
- Verizon store inventory is not supported by this source.
- Do not store secrets in the public repo. GitHub Actions writes to `history.json` in your public repository.
