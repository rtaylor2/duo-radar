"""Called only after state was successfully committed and pushed."""
import json
from pathlib import Path
from alerts import notify
path=Path('pending_alerts.json')
rows=json.loads(path.read_text()) if path.exists() else []
notify(rows)
