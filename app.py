import datetime as dt
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from inventory_core import APPLE, fetch, flatten, now, parse_time, sightings

st.set_page_config(page_title='Rons Iphone Duo Radar | Nationwide Pickup',page_icon='📱',layout='wide')
st.markdown('''<style>.stApp{background:#0b1020;color:#e9eefc}.block-container{padding-top:1.5rem;max-width:1450px}h1,h2,h3{letter-spacing:-.025em}[data-testid="stMetric"]{background:#151d31;border:1px solid #2b3550;padding:15px;border-radius:14px}a{color:#85bdff!important}</style>''',unsafe_allow_html=True)
st.title('📱 Ron's Iphone Duo Radar')
st.caption('Nationwide Apple Store pickup • 24-hour observed history • unofficial third-party feed')
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
st.subheader('Last 24 hours · Observed inventory history')
h=history()
if not h:
    st.info('No stored observations yet. Enable the included GitHub Actions collector to build history. This section does not invent earlier restocks.')
else:
    st.caption(f'{len(h)} saved successful observations, from {h[0]["observed_at"]} to {h[-1]["observed_at"]} UTC. This is observed inventory, not a verified log of shipment arrivals or actual restock times.')
    chart=pd.DataFrame([{'Time':parse_time(s['observed_at']),'Reported configurations':len(s.get('items',[])),'Stores reporting':len({(r.get('Store ID') or r.get('Store'),r.get('City'),r.get('State')) for r in s.get('items',[])})} for s in h])
    st.line_chart(chart.set_index('Time'))
    events=sightings(h)
    if events:
        st.dataframe(pd.DataFrame([{k:r.get(k,'') for k in ['Store','City','State','Storage','Color','First seen','Last seen','Observations']} for r in events]),hide_index=True,use_container_width=True)
    else: st.caption('No positive inventory sightings in recorded observations.')
    if st.button('Reload stored history'):
        history.clear();st.rerun()
st.divider()
st.caption('Sources: [PickupChecker](https://pickupchecker.com/iphone-duo-stock-checker) · [Apple checkout](https://www.apple.com/shop/buy-iphone). Unofficial feed; verify its permitted use and limits. GitHub Actions schedules are best-effort and may be delayed. Free Streamlit hosting can sleep when idle.')
