"""Poll public Apple inventory; persist queue before delivery. No live alerts on first run."""
import json
from pathlib import Path
from inventory_core import fetch,record
from alerts import select_new

def load(path,default):
    return json.loads(path.read_text()) if path.exists() else default

history_path=Path('history.json'); state_path=Path('alert_state.json'); queue_path=Path('pending_alerts.json')
history=load(history_path,[]); state=load(state_path,{}); queue=load(queue_path,[])
payload=fetch(); updated_history=record(history,payload)
new,updated=select_new(payload,state)
known={r['key'] for r in queue}
queue.extend(r for r in new if r['key'] not in known)
history_path.write_text(json.dumps(updated_history,indent=2)+'\n')
state_path.write_text(json.dumps(updated,indent=2)+'\n')
queue_path.write_text(json.dumps(queue,indent=2)+'\n')
print(f'Observed {len(updated["active"])} listings; {len(new)} new; pending={len(queue)}; baseline={not state.get("initialized")}')
