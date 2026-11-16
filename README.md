# Ron's iPhone Duo Radar — consolidated update v4

This is a complete replacement of the dashboard application files. It includes:

- Correctly quoted `Ron's iPhone Duo Radar` title and browser tab title.
- Live US Apple Store inventory reported by PickupChecker, with freshness warning.
- Last 24 hours of reported restocks loaded directly from PickupChecker's restock API (maximum 200 events per response).
- Map of currently reported inventory **only when the feed provides coordinates**. Missing coordinates are not invented.
- Apple ordering-page links (not guaranteed direct store/configuration checkout).
- Optional 10-minute GitHub Actions inventory snapshot workflow.

Verizon inventory is **not** covered by these Apple Store feeds. No source is claimed to provide a confirmed purchase or reservation.

## Deploy in one update

Extract the ZIP. Copy **all** its contents, including the hidden `.github` directory, into the root of your existing local `duo_web_dashboard` Git repository, replacing matching files. Do not replace or delete your `.git` directory.

```bash
cd ~/Downloads/duo_web_dashboard
python3 -m py_compile app.py inventory_core.py collect.py
git add app.py inventory_core.py collect.py requirements.txt README.md history.json .github/workflows/inventory-history.yml
git commit -m "Consolidate title fix, live map, 24h history and order links"
git push
```

The syntax check should print nothing on success. Verify the published app after Streamlit redeploys. GitHub Actions scheduled jobs can be delayed. Streamlit may sleep when idle. Historical restock status is a provider observation and should be rechecked at Apple.

Source: https://pickupchecker.com/iphone-duo-stock-api — attribution required by the provider. API response has not been end-to-end tested in this runtime.
