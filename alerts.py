"""Notification helpers. No notification is sent without a fresh timestamped feed."""
import datetime as dt
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote
import requests
from inventory_core import APPLE, flatten, now, parse_time


def is_fresh(payload, observed=None):
    observed = observed or now()
    t = parse_time(payload.get('generated_at') or payload.get('updated_at'))
    return t is not None and dt.timedelta(minutes=-5) <= observed-t <= dt.timedelta(minutes=10)


def fingerprint(row):
    return row['key']


def select_new(payload, state):
    """First valid run establishes baseline; subsequent runs alert only on transitions absent->present."""
    if not is_fresh(payload):
        raise ValueError('No recent provider timestamp: refusing to send availability alerts')
    rows = flatten(payload)
    current = {fingerprint(row): row for row in rows}
    previous = set(state.get('active', []))
    initialized = bool(state.get('initialized'))
    new = [row for key, row in current.items() if key not in previous] if initialized else []
    updated = {'initialized': True, 'active': sorted(current), 'last_poll': now().isoformat(),
               'last_new': [dict(row, detected_at=now().isoformat()) for row in new][:100]}
    return new, updated


def alert_message(rows):
    first = rows[0]
    headline = f"iPhone Duo pickup: {len(rows)} new listing(s)"
    lines = [headline, 'Newly observed in the public feed; NOT confirmed reservable.', '']
    for r in rows[:12]:
        lines.append(f"{r['Store']} — {r['City']}, {r['State']} — {r['Storage']} {r['Color']}")
    if len(rows)>12: lines.append(f"...and {len(rows)-12} more")
    lines.extend(['', f'Check Apple ordering: {APPLE}', 'Verify store and configuration before traveling.'])
    return headline, '\n'.join(lines)


def send_ntfy(title, body):
    topic = os.getenv('NTFY_TOPIC', '').strip()
    if not topic: return False
    # ntfy.sh topic names are shared namespaces: use a long random topic and do not publish it.
    if not all(c.isalnum() or c in '_-' for c in topic):
        raise ValueError('NTFY_TOPIC must contain only letters, digits, _ or -')
    server = os.getenv('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')
    if not server.startswith('https://'): raise ValueError('NTFY_SERVER must be HTTPS')
    headers = {'Title': title.encode('ascii','ignore').decode() or 'iPhone Duo stock',
               'Click': APPLE, 'Priority': 'high', 'Tags': 'iphone,shopping_cart'}
    token = os.getenv('NTFY_TOKEN')
    if token: headers['Authorization'] = f'Bearer {token}'
    r = requests.post(f'{server}/{quote(topic)}', data=body.encode('utf-8'),
                      headers=headers, timeout=20)
    r.raise_for_status()
    return True


def send_email(title, body):
    host = os.getenv('SMTP_HOST','').strip()
    to = os.getenv('ALERT_EMAIL_TO','').strip()
    user = os.getenv('SMTP_USERNAME','').strip()
    password = os.getenv('SMTP_PASSWORD','')
    if not all((host,to,user,password)): return False
    msg = EmailMessage()
    msg['Subject'] = title
    msg['From'] = os.getenv('ALERT_EMAIL_FROM',user)
    msg['To'] = to
    msg.set_content(body)
    with smtplib.SMTP_SSL(host, int(os.getenv('SMTP_PORT','465')), context=ssl.create_default_context(), timeout=20) as smtp:
        smtp.login(user,password)
        smtp.send_message(msg)
    return True


def notify(rows):
    if not rows: return
    title, body = alert_message(rows)
    failures=[]
    for label, sender in [('ntfy',send_ntfy),('email',send_email)]:
        try:
            enabled=sender(title,body)
            print(f'{label}: {"sent" if enabled else "not configured"}')
        except Exception as exc:
            failures.append(f'{label}: {exc}')
    if failures:
        raise RuntimeError('; '.join(failures))
