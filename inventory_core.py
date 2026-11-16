"""Shared feed normalization and 24h observed history. Unofficial provider."""
import datetime as dt
import os
import requests

API = os.getenv('DUO_STOCK_API', 'https://pickupchecker.com/api/v1/us/stock?model=duo')
APPLE = 'https://www.apple.com/shop/buy-iphone'

def now():
    return dt.datetime.now(dt.timezone.utc)

def iso(t):
    return t.isoformat(timespec='seconds').replace('+00:00','Z')

def parse_time(value):
    if not value: return None
    try:
        t=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)
    except (ValueError, TypeError): return None

def fetch():
    r=requests.get(API,timeout=20,headers={'User-Agent':'DuoRadar/2.0 (public dashboard)','Accept':'application/json'})
    r.raise_for_status()
    p=r.json()
    if not isinstance(p,dict) or not isinstance(p.get('stores'),list):
        raise ValueError('Unexpected feed schema: expected object with stores array')
    return p

def val(x): return str(x).strip() if x is not None else ''

def flatten(p):
    out=[]
    for s in p['stores']:
        if not isinstance(s,dict): continue
        store=val(s.get('name') or s.get('store_name') or 'Unknown store')
        city=val(s.get('city')); state=val(s.get('state') or s.get('state_code'))
        sid=val(s.get('store_number') or s.get('store_id'))
        zip_code=val(s.get('zip') or s.get('zipcode') or s.get('postal_code'))
        lat=s.get('latitude',s.get('lat')); lon=s.get('longitude',s.get('lon',s.get('lng')))
        try:
            lat=float(lat); lon=float(lon)
            if not (-90<=lat<=90 and -180<=lon<=180): lat=lon=None
        except (ValueError,TypeError): lat=lon=None
        items=s.get('available') or []
        if not isinstance(items,list): continue
        for a in items:
            if not isinstance(a,dict): continue
            storage=val(a.get('storage')); color=val(a.get('color')); part=val(a.get('part_number'))
            key='|'.join((sid or f'{store}/{city}/{state}',part or f'{storage}/{color}'))
            out.append({'key':key,'Store':store,'City':city,'State':state,'ZIP':zip_code,'Storage':storage,'Color':color,'Part':part,'Store ID':sid,'lat':lat,'lon':lon})
    return out

def record(history, p, observed_at=None):
    """Record successful poll only. Prevent stale feed from being presented as new events."""
    observed_at=observed_at or now()
    provider_time=parse_time(p.get('generated_at') or p.get('updated_at'))
    if provider_time and provider_time > observed_at + dt.timedelta(minutes=5):
        raise ValueError('Provider timestamp is in the future')
    if provider_time and observed_at-provider_time > dt.timedelta(minutes=10):
        raise ValueError('Provider data older than 10 minutes; not recording as current')
    rows=flatten(p)
    sample={'observed_at':iso(observed_at),'provider_at':iso(provider_time) if provider_time else None,
            'items':[{k:v for k,v in r.items() if k!='key'} | {'key':r['key']} for r in rows]}
    prior=[s for s in history if isinstance(s,dict) and parse_time(s.get('observed_at')) and parse_time(s['observed_at'])>=observed_at-dt.timedelta(hours=24)]
    if not prior or prior[-1].get('provider_at')!=sample['provider_at'] or prior[-1].get('items')!=sample['items']:
        prior.append(sample)
    return prior[-500:]

def sightings(history):
    """Distinct stock sightings and first observed time; not proof of actual restock."""
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
