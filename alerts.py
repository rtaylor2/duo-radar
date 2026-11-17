"""Push alerts for fresh third-party Apple Store pickup observations only."""
import datetime as dt
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote
import requests
from inventory_core import flatten, now, parse_time, fresh

def select_new(payload,state):
    rows=flatten(payload)
    current={r['key']:r for r in rows}
    previous=set(state.get('active',[]))
    initialized=bool(state.get('initialized'))
    new=[r for key,r in current.items() if key not in previous] if initialized else []
    updated={'initialized':True,'active':sorted(current),'last_poll':now().isoformat(),
             'last_new':[dict(r,detected_at=now().isoformat()) for r in new][:100]}
    return new,updated

def alert_message(row):
    title=f"iPhone Duo pickup reported: {row['Store']}"
    body=(f"Retailer: {row['Retailer']} (third-party reported, not checkout verified)\n"
          f"Store: {row['Store']}\nLocation: {row['City']}, {row['State']}\n"
          f"Configuration: {row['Storage']} {row['Color']} ({row['Part']})\n"
          f"Store checked: {row['observed_at']}\n"
          f"Store-specific stock source: {row['source_url']}\n"
          f"Direct pickup/checkout link: {row.get('pickup_url') or 'Not available from source'}\n"
          'Verify pickup before traveling. Shipping is not pickup.')
    return title,body

def send_ntfy(title,body,link):
    topic=os.getenv('NTFY_TOPIC','').strip()
    if not topic: return False
    if not all(c.isalnum() or c in '_-' for c in topic): raise ValueError('Invalid NTFY_TOPIC')
    server=os.getenv('NTFY_SERVER','https://ntfy.sh').rstrip('/')
    if not server.startswith('https://'): raise ValueError('NTFY_SERVER must be HTTPS')
    headers={'Title':title.encode('ascii','ignore').decode() or 'iPhone Duo stock',
             'Click':link,'Priority':'high','Tags':'iphone,shopping_cart'}
    token=os.getenv('NTFY_TOKEN')
    if token: headers['Authorization']=f'Bearer {token}'
    r=requests.post(f'{server}/{quote(topic)}',data=body.encode('utf-8'),headers=headers,timeout=20)
    r.raise_for_status()
    return True

def send_email(title,body):
    host=os.getenv('SMTP_HOST','').strip(); to=os.getenv('ALERT_EMAIL_TO','').strip()
    user=os.getenv('SMTP_USERNAME','').strip(); password=os.getenv('SMTP_PASSWORD','')
    if not all((host,to,user,password)): return False
    msg=EmailMessage(); msg['Subject']=title; msg['From']=os.getenv('ALERT_EMAIL_FROM',user)
    msg['To']=to; msg.set_content(body)
    with smtplib.SMTP_SSL(host,int(os.getenv('SMTP_PORT','465')),context=ssl.create_default_context(),timeout=20) as smtp:
        smtp.login(user,password); smtp.send_message(msg)
    return True

def deliver(row):
    # A positive provider observation is sufficient for fast alert mode, but never claim checkout verification.
    if row.get('Retailer')!='Apple' or not row.get('source_url') or not fresh(parse_time(row.get('observed_at'))):
        return 'expired'
    title,body=alert_message(row)
    enabled=[]
    if os.getenv('NTFY_TOPIC','').strip(): enabled.append(('ntfy',lambda:send_ntfy(title,body,row.get('pickup_url') or row['source_url'])))
    if all(os.getenv(k) for k in ('SMTP_HOST','ALERT_EMAIL_TO','SMTP_USERNAME','SMTP_PASSWORD')):
        enabled.append(('email',lambda:send_email(title,body)))
    if not enabled: raise RuntimeError('No alert delivery channel configured')
    for name,fn in enabled:
        fn()
        print(f'{name}: accepted for {row["key"]}')
    return 'sent'

def is_fresh(payload, observed=None):
    """Check that the inventory feed has a recent timestamp."""
    import datetime as dt
    from inventory_core import now, parse_time

    observed = observed or now()
    t = parse_time(payload.get("generated_at") or payload.get("updated_at"))

    return (
        t is not None
        and dt.timedelta(minutes=-5)
        <= observed - t
        <= dt.timedelta(minutes=10)
    )
