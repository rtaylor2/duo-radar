import datetime as dt
import json
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from inventory_core import APPLE, fetch, flatten, now, parse_time, sightings

st.set_page_config(page_title="Ron's iPhone Duo Radar",page_icon='📱',layout='wide')
st.markdown('''<style>.stApp{background:#0b1020;color:#e9eefc}.block-container{padding-top:1.5rem;max-width:1450px}h1,h2,h3{letter-spacing:-.025em}[data-testid="stMetric"]{background:#151d31;border:1px solid #2b3550;padding:15px;border-radius:14px}a{color:#85bdff!important}</style>''',unsafe_allow_html=True)
st.title("📱 Ron's iPhone Duo Radar")
st.caption('Nationwide Apple Store pickup • Last 24 hours of reported restocks • Source: PickupChecker')
st.info('Apple Store inventory only — Verizon corporate-store stock is not available through this feed. A reported listing is not a reservation.')

@st.cache_data(ttl=25,show_spinner=False)
def live(): return fetch()

@st.cache_data(ttl=60,show_spinner=False)
def history():
    path=Path(__file__).with_name('history.json')
    if not path.exists(): return []
    samples=json.loads(path.read_text())
    cutoff=now()-dt.timedelta(hours=24)
    return [s for s in samples if parse_time(s.get('observed_at')) and parse_time(s['observed_at'])>=cutoff]

@st.fragment(run_every='30s')
def panel():
    st.subheader('Current reported availability')
    try:
        payload=live(); rows=flatten(payload)
        stamp=payload.get('generated_at') or payload.get('updated_at')
        provider_time=parse_time(stamp)
        age=(now()-provider_time).total_seconds()/60 if provider_time else None
        if age is not None and (age>10 or age < -5):
            st.error(f'Feed timestamp is stale or invalid ({stamp}). Listings below are not verified as current.')
            fresh=False
        elif age is None:
            st.warning('Feed does not provide a parseable timestamp; stock freshness cannot be confirmed.')
            fresh=False
        else: fresh=True
    except Exception as exc:
        st.error(f'Live feed unavailable: {exc}. This does not mean sold out.')
        if st.button('Retry live feed'):
            live.clear();st.rerun(scope='fragment')
        return
    count=len({(r['Store ID'] or r['Store'],r['City'],r['State']) for r in rows})
    a,b,c=st.columns(3)
    a.metric('Stores reporting stock',count)
    b.metric('Reported configurations',len(rows))
    c.metric('Stores in feed',len(payload['stores']))
    st.caption(f'Provider timestamp: {stamp or "not supplied"} · Refreshed every 30s while the page is open · API responses cached 25s')
    x,y,z=st.columns([2,1,1])
    q=x.text_input('Search store or city',placeholder='Search all US stores')
    state=y.selectbox('State',['All']+sorted({r['State'] for r in rows if r['State']}))
    storage=z.selectbox('Capacity',['All']+sorted({r['Storage'] for r in rows if r['Storage']}))
    filtered=[r for r in rows if (not q or q.lower() in (r['Store']+' '+r['City']).lower()) and (state=='All' or r['State']==state) and (storage=='All' or r['Storage']==storage)]
    if not rows: st.warning('No pickup configurations reported in this feed. Not a guarantee of no stock.')
    elif not filtered: st.info('No matching listings under these filters.')
    else:
        if fresh: st.success(f'{len(filtered)} reported configurations — verify immediately in Apple checkout')
        st.dataframe(pd.DataFrame([{k:r[k] for k in ['Store','City','State','Storage','Color','Part']} for r in filtered]),hide_index=True,use_container_width=True)
        st.markdown('**Order links** (Apple checkout requires selecting the configuration and store; no guaranteed direct reservation URL):')
        for r in filtered[:40]:
            st.markdown(f'- **{r["Store"]}, {r["City"]} {r["State"]} — {r["Storage"]} {r["Color"]}** · [Open Apple checkout]({APPLE})')
        if len(filtered)>40: st.caption('Showing the first 40 links; use filters to narrow the results.')
    st.subheader('Live stock map')
    geocoded=[r for r in filtered if r['lat'] is not None and r['lon'] is not None]
    if geocoded:
        pts=pd.DataFrame(geocoded)
        st.map(pts,latitude='lat',longitude='lon',size=100)
        st.caption(f'{len(geocoded)} configurations have coordinates supplied by the provider; other stores are not plotted. Pins represent reported inventory, not confirmed reservations.')
    else:
        st.info('No store coordinates are available in the live feed for these results. The map will populate automatically if the provider supplies coordinates. No store locations are guessed.')
    if st.button('Refresh now',type='primary'):
        live.clear();st.rerun(scope='fragment')

panel()
st.divider()
st.subheader('Last 24 hours · Reported restocks')
st.caption('Historical restock events supplied by PickupChecker, not inferred from our own empty snapshots. Event times are provider observations, not shipment arrivals. All times shown in UTC.')

@st.cache_data(ttl=120, show_spinner=False)
def external_restocks():
    url='https://pickupchecker.com/api/v1/us/restocks'
    response=requests.get(url,params={'model':'duo','hours':24,'limit':200},timeout=20,
                          headers={'User-Agent':'RonDuoRadar/3.0 (public dashboard)','Accept':'application/json'})
    response.raise_for_status()
    data=response.json()
    if isinstance(data,list): return data
    if not isinstance(data,dict): raise ValueError('Unexpected history response')
    events=data.get('restocks')
    if not isinstance(events,list): raise ValueError('History response has no restocks list')
    return events

try:
    events=external_restocks()
    cutoff=now()-dt.timedelta(hours=24)
    display=[]
    for event in events:
        if not isinstance(event,dict): continue
        observed=parse_time(event.get('at'))
        if observed is None or not cutoff<=observed<=now()+dt.timedelta(minutes=5): continue
        store=event.get('store') or {}
        config=event.get('configuration') or {}
        if isinstance(store,str): store={'name':store}
        if isinstance(config,str): config={'name':config}
        if not isinstance(store,dict): store={}
        if not isinstance(config,dict): config={}
        listed=event.get('still_listed')
        display.append({
            'Detected (UTC)':observed,
            'Store':store.get('name') or store.get('store_name') or event.get('store_name') or 'Unknown',
            'City':store.get('city') or event.get('city') or '',
            'State':store.get('state') or event.get('state') or '',
            'Storage':config.get('storage') or event.get('storage') or '',
            'Color':config.get('color') or event.get('color') or config.get('name') or '',
            'Status': 'Still listed (recheck)' if listed is True else ('Sold out' if listed is False else 'Unknown'),
            'Apple order page':APPLE,
        })
    display.sort(key=lambda e:e['Detected (UTC)'],reverse=True)
    a,b,c=st.columns(3)
    a.metric('Reported restock events',len(display))
    b.metric('Still listed by source',sum(e['Status']=='Still listed (recheck)' for e in display))
    c.metric('Stores with events',len({(e['Store'],e['City'],e['State']) for e in display}))
    if display:
        df=pd.DataFrame(display)
        st.dataframe(df,hide_index=True,use_container_width=True,
            column_config={'Detected (UTC)':st.column_config.DatetimeColumn(format='YYYY-MM-DD HH:mm:ss'),
                           'Apple order page':st.column_config.LinkColumn('Order at Apple',display_text='Open Apple')})
        by_hour=df.set_index('Detected (UTC)').resample('1h').size().rename('Restock events')
        st.bar_chart(by_hour)
        st.caption('Source: [PickupChecker](https://pickupchecker.com/iphone-duo-stock-api). The API limits a response to 200 events. If 200 are returned, this may not represent every event in the last 24 hours.')
    else:
        st.info('The provider returned no dated restock events for the last 24 hours.')
    if st.button('Refresh reported history'):
        external_restocks.clear();st.rerun()
except Exception as exc:
    st.warning(f'Historical provider feed unavailable or changed format: {exc}')
    st.markdown('[View reported restocks at FindInStock](https://findinstock.com/iphone-duo/restocks)')

with st.expander('Our own collected inventory observations'):
    h=history()
    if not h:
        st.caption('No local snapshots collected yet. The historical feed above does not depend on GitHub Actions.')
    else:
        st.caption(f'{len(h)} saved observations. These are independent of the third-party restock events above.')
        chart=pd.DataFrame([{'Time':parse_time(s['observed_at']),'Reported configurations':len(s.get('items',[]))} for s in h])
        st.line_chart(chart.set_index('Time'))
        seen=sightings(h)
        if seen: st.dataframe(pd.DataFrame(seen),hide_index=True,use_container_width=True)
st.divider()
st.caption('Sources: [PickupChecker](https://pickupchecker.com/iphone-duo-stock-checker) · [Apple checkout](https://www.apple.com/shop/buy-iphone). Unofficial feed; verify its permitted use and limits. GitHub Actions schedules are best-effort and may be delayed. Free Streamlit hosting can sleep when idle.')
