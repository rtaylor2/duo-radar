# Ron's iPhone Duo Radar v5

Streamlit inventory dashboard with nationwide Apple Store public-feed monitoring, 24-hour third-party restock history, available store map pins, and alerts.

## Important limitations

- The unofficial PickupChecker endpoints and their JSON schemas have **not been verified live** here. An API error, changed response, stale timestamp, or no records is **not** proof of no stock.
- The collector currently covers **Apple Store listings only**, not Verizon corporate stores. Do not describe it as nationwide Verizon monitoring until a verified Verizon integration is added.
- The checkout link opens Apple's general iPhone ordering page, not a guaranteed SKU/store-specific reservation. Confirm the model, capacity, color and pickup location yourself.
- GitHub Actions cron schedules are **best effort** and can be delayed. This is not instantaneous stock monitoring.
- First successful fresh poll initializes the alert baseline and deliberately **does not notify** for existing listings. Later polls alert on absent-to-present transitions. If a listing disappears and returns, it can alert again.
- Notification state is committed to GitHub before delivery to avoid repeated alerts on subsequent runs. If the notification provider fails after the state is saved, that event may not be retried automatically.
- `ntfy.sh` public topics are not access-controlled: use a **long random topic**; anyone who knows it can subscribe. For confidential alerts use a self-hosted ntfy instance with authentication.

## Deploy

Copy the contents of this folder over your existing repository, excluding any `.git` folder. Verify and push:

```bash
python3 -m py_compile app.py inventory_core.py collect.py alerts.py send_alerts.py
git status --short
git add app.py inventory_core.py collect.py alerts.py send_alerts.py requirements.txt README.md .github/workflows/inventory-history.yml .gitignore alert_state.json
git commit -m "Add push email and screen inventory alerts"
git pull --rebase origin main
git push origin main
```

If a merge conflict occurs, stop and inspect before continuing. Do not force push. The collector also writes `history.json`; do not accidentally overwrite it with an empty local copy.

## Configure push alerts on iPhone (ntfy)

1. Install the **ntfy** iOS app and subscribe to a unique, randomly generated topic (e.g., generated with `python3 -c 'import secrets; print(secrets.token_urlsafe(24))'`).
2. In your GitHub repository, navigate to **Settings → Secrets and variables → Actions → New repository secret**.
3. Create secret `NTFY_TOPIC` with the exact topic. Optional `NTFY_SERVER` defaults to `https://ntfy.sh`. If using an authenticated server, set `NTFY_TOKEN`.
4. Allow notifications in iOS settings. Test using the GitHub Actions workflow after initial baseline; see below.

## Configure email alerts

Add GitHub Actions repository secrets:

| Secret | Value |
|---|---|
| `SMTP_HOST` | e.g. `smtp.gmail.com` for Gmail |
| `SMTP_PORT` | `465` (optional; default) |
| `SMTP_USERNAME` | SMTP login address |
| `SMTP_PASSWORD` | SMTP app password / provider-specific token (not your normal password) |
| `ALERT_EMAIL_TO` | recipient email address |
| `ALERT_EMAIL_FROM` | optional sender address; defaults to SMTP username |

For Gmail, app passwords generally require two-step verification and eligible account settings. Never put credentials in Git-tracked files or Streamlit source code.

## Test

1. GitHub **Actions → Collect inventory and send alerts → Run workflow**. The first valid poll establishes a baseline without alerts. If the feed is invalid or stale, the job fails safely.
2. To test notification delivery without inventing a real stock event, run the commands below **locally** with temporary environment variables (never commit them), or add a separate manual workflow later:

```bash
python3 - <<'PY'
from alerts import notify
notify([{'Store':'TEST ONLY','City':'Example','State':'US','Storage':'256 GB','Color':'Black'}])
PY
```

This will send a clearly labeled TEST ONLY alert if environment variables are configured.

## Dashboard

The Streamlit page refreshes its current availability section about every 30 seconds while open. `st.toast` shows a notification for new keys after its first successful fresh poll. Browser/OS-level push while the tab is closed comes from ntfy, not Streamlit.
