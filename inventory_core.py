"""Unofficial Apple pickup feed. Positive observations are not checkout guarantees."""
import datetime as dt
import json
import os
from urllib.parse import urlparse
import requests

API = os.getenv('DUO_STOCK_API', 'https://pickupchecker.com/api/v1/us/stock?model=duo')
APPLE = 'https://www.apple.com/shop/buy-iphone'
MAX_AGE_SECONDS = 120

def now():
    return dt.datetime.now(dt.timezone.utc)

def iso(t):
    return t.astimezone(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

def parse_time(value):
    if not value: return None
    try:
        t = dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)
    except (ValueError, TypeError): return None

def fresh(t, at=None, max_age=MAX_AGE_SECONDS):
    at = at or now()
    return t is not None and -30 <= (at-t).total_seconds() <= max_age

def valid_url(value):
    if not isinstance(value, str): return None
    try:
        u=urlparse(value.strip())
        if u.scheme == 'https' and u.netloc and not any(c in value for c in '[]() '):
            return value.strip()
    except ValueError: pass
    return None

def fetch():
    r=requests.get(API,timeout=20,headers={'User-Agent':'DuoRadar/6.0 (public dashboard)','Accept':'application/json'})
    r.raise_for_status()
    p=r.json()
    if not isinstance(p,dict) or not isinstance(p.get('stores'),list):
        raise ValueError('Unexpected feed schema: stores array missing')
    return p

def flatten(p, at=None):
    """Only current positive Apple Store observations, with store-specific source links."""
    at=at or now()
    provider=parse_time(p.get('generated_at') or p.get('updated_at'))
    if not fresh(provider,at):
        raise ValueError('Provider timestamp absent or older than 2 minutes')
    out=[]
    for s in p['stores']:
        if not isinstance(s,dict) or s.get('in_stock') is not True: continue
        checked=parse_time(s.get('last_checked_at'))
        if not fresh(checked,at): continue
        items=s.get('available')
        if not isinstance(items,list) or not items: continue
        sid=str(s.get('store_number') or s.get('store_id') or '').strip()
        store=str(s.get('name') or s.get('store_name') or '').strip()
        city=str(s.get('city') or '').strip()
        state=str(s.get('state') or s.get('state_code') or s.get('region') or '').strip()
        # Source store URL is evidence/details, NOT a checkout or reservation URL.
        store_url=valid_url(s.get('url'))
        if not all((sid,store,city,state,store_url)): continue
        lat=s.get('latitude',s.get('lat')); lon=s.get('longitude',s.get('lon',s.get('lng')))
        try:
            lat=float(lat); lon=float(lon)
            if not (-90<=lat<=90 and -180<=lon<=180): lat=lon=None
        except (ValueError,TypeError): lat=lon=None
        for a in items:
            if not isinstance(a,dict): continue
            storage=str(a.get('storage') or '').strip()
            color=str(a.get('color') or '').strip()
            part=str(a.get('part_number') or '').strip()
            if not storage or not color or not part: continue
            key=f'Apple|{sid}|{part}'
            out.append({'key':key,'Retailer':'Apple','Store':store,'City':city,'State':state,
                        'ZIP':str(s.get('zip') or s.get('zipcode') or ''),'Storage':storage,
                        'Color':color,'Part':part,'Store ID':sid,'lat':lat,'lon':lon,
                        'observed_at':iso(checked),'source_url':store_url,
                        'pickup_url':valid_url(a.get('pickup_url') or a.get('checkout_url'))})
    return out

def record(history,p,observed_at=None):
    at=observed_at or now()
    provider=parse_time(p.get('generated_at') or p.get('updated_at'))
    rows=flatten(p,at)
    sample={'observed_at':iso(at),'provider_at':iso(provider),'items':rows}
    prior=[s for s in history if isinstance(s,dict) and (t:=parse_time(s.get('observed_at'))) and t>=at-dt.timedelta(hours=24)]
    if not prior or prior[-1].get('provider_at')!=sample['provider_at'] or prior[-1].get('items')!=sample['items']:
        prior.append(sample)
    return prior[-500:]

def sightings(history):
    found={}
    for sample in history:
        for item in sample.get('items',[]):
            key=item.get('key')
            if not key: continue
            if key not in found:
                found[key]={**item,'First seen':sample['observed_at'],'Last seen':sample['observed_at'],'Observations':1}
            else:
                found[key]['Last seen']=sample['observed_at']
                found[key]['Observations']+=1
    return sorted(found.values(),key=lambda r:r['Last seen'],reverse=True)
