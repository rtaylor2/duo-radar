"""GitHub Actions collector. Persist baseline before notifications to avoid duplicates."""
import json
from pathlib import Path
from inventory_core import fetch, record
from alerts import select_new, notify

history_path=Path('history.json')
state_path=Path('alert_state.json')
history=json.loads(history_path.read_text()) if history_path.exists() else []
state=json.loads(state_path.read_text()) if state_path.exists() else {}
payload=fetch()
new_history=record(history,payload)
new, updated=select_new(payload,state)
history_path.write_text(json.dumps(new_history,indent=2)+'\n')
state_path.write_text(json.dumps(updated,indent=2)+'\n')
print(f'Observed {len(updated["active"])} listings; {len(new)} new; baseline={not state.get("initialized")}')
# Delivery is performed after state writes; workflow commits both files before sending.
Path('pending_alerts.json').write_text(json.dumps(new,indent=2)+'\n')
