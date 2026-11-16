"""Run by GitHub Actions; writes snapshots only on successful, fresh feed responses."""
import json
from pathlib import Path
from inventory_core import fetch, record

path=Path('history.json')
history=json.loads(path.read_text()) if path.exists() else []
new=record(history,fetch())
path.write_text(json.dumps(new,indent=2)+'\n')
print(f'Saved {len(new)} observations; latest contains {len(new[-1]["items"])} configurations')
