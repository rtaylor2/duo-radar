# Duo Radar — shareable Apple pickup dashboard

A public, read-only Streamlit dashboard for nationwide iPhone Duo Apple Store pickup availability. Uses the unofficial third-party PickupChecker endpoint `https://pickupchecker.com/api/v1/us/stock?model=duo`.

## Run on your Mac

```bash
cd ~/Downloads/duo_web_dashboard
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Streamlit prints a local URL (usually http://localhost:8501). Keep Terminal open.

## Publish free with Streamlit Community Cloud

1. Create a GitHub repository, for example `duo-radar`.
2. Upload `app.py`, `requirements.txt`, and this README to the repository root.
3. Visit https://share.streamlit.io/ and sign in with GitHub.
4. Select **Create app**, choose your repository and branch, and set the entry point to `app.py`.
5. Deploy. Streamlit provides a public URL you can send to your friend.

The app refreshes every 30 seconds **while the browser tab is open**. It does not send background alerts or run a continuously polling server when no one is viewing it. Free hosting may sleep when idle.

## Important limitations

- Apple Store pickup only; **no Verizon corporate-store inventory**.
- The data feed is third-party, unofficial, and may be unavailable, change schema, or limit public use. Confirm permission and rate limits before publishing widely.
- The API endpoint was taken from the existing CLI tracker and has **not been live-validated in this build**. An error banner is shown if it fails; errors are never displayed as sold-out inventory.
- Reported stock is not a reservation. Always confirm in Apple's checkout.
- No passwords, payment data, or private tokens are required.
- The dashboard uses Streamlit's 25-second cache to reduce repeated upstream requests, including when multiple viewers open it.

## Optional API override

Set environment variable `DUO_STOCK_API` to an authorized compatible JSON endpoint. Expected response shape:

```json
{"generated_at":"2026-11-16T16:00:00Z","stores":[{"name":"Example Store","city":"Example City","state":"NC","store_number":"R001","available":[{"storage":"256GB","color":"White","part_number":"EXAMPLE"}]}]}
```
