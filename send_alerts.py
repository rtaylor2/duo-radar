"""Deliver persisted alerts. Keep failed alerts queued; discard expired alerts."""
import json
from pathlib import Path
from alerts import deliver
path=Path('pending_alerts.json')
rows=json.loads(path.read_text()) if path.exists() else []
remaining=[]; errors=[]
for i,row in enumerate(rows):
    try:
        result=deliver(row)
        print(f'{row.get("key")}: {result}')
    except Exception as exc:
        remaining.append(row)
        errors.append(f'{row.get("key")}: {exc}')
# Write after processing, preserving unsuccessful deliveries for next workflow run.
path.write_text(json.dumps(remaining,indent=2)+'\n')
if errors: raise RuntimeError('; '.join(errors))
