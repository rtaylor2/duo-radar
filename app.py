"""Public, read-only iPhone Duo pickup dashboard."""
import datetime as dt
import os
import requests
import streamlit as st

API = os.getenv('DUO_STOCK_API', 'https://pickupchecker.com/api/v1/us/stock?model=duo')
APPLE = 'https://www.apple.com/shop/buy-iphone'
st.set_page_config(page_title='Duo Radar | Pickup Availability', page_icon='📱', layout='wide')
st.markdown('''<style>
.stApp {background: #0b1020; color: #e9eefc;}
.block-container {padding-top: 2rem; max-width: 1350px;}
h1,h2,h3 {letter-spacing:-.035em;}
[data-testid="stMetric"] {background:#151d31;border:1px solid #2b3550;padding:16px;border-radius:16px;}
[data-testid="stMetricLabel"] {color:#a9b6d0;}
[data-testid="stMetricValue"] {color:#f4f7ff;}
a {color:#83bbff!important;}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=25, show_spinner=False)
def get_inventory():
    response = requests.get(API, timeout=18, headers={'User-Agent':'DuoRadarDashboard/1.0', 'Accept':'application/json'})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get('stores'), list):
        raise ValueError('The inventory provider returned an unexpected data format.')
    return payload

def clean(value):
    return str(value).strip() if value is not None else ''

def flatten(data):
    result=[]
    for store in data['stores']:
        if not isinstance(store, dict):
            continue
        name=clean(store.get('name') or store.get('store_name') or 'Unknown Apple Store')
        city=clean(store.get('city'))
        state=clean(store.get('state') or store.get('state_code'))
        number=clean(store.get('store_number') or store.get('store_id'))
        for item in store.get('available', []):
            if not isinstance(item, dict):
                continue
            result.append({'Store':name, 'City':city, 'State':state, 'Storage':clean(item.get('storage')), 'Color':clean(item.get('color')), 'Part number':clean(item.get('part_number')), 'Store ID':number})
    return result

st.title('📱 Duo Radar')
st.caption('Nationwide Apple Store pickup availability • Independent, unofficial dashboard')
st.info('Apple inventory only. Verizon corporate-store inventory is not available from this feed. Availability may change before checkout.', icon='ℹ️')

@st.fragment(run_every='30s')
def inventory_panel():
    try:
        data=get_inventory()
        rows=flatten(data)
    except (requests.RequestException, ValueError, TypeError) as exc:
        st.error(f'Inventory feed unavailable: {exc}. This does NOT mean stores are sold out.')
        st.caption('Check the source directly or try Refresh now.')
        if st.button('Retry now'):
            get_inventory.clear()
            st.rerun(scope='fragment')
        return
    timestamp=data.get('generated_at') or data.get('updated_at') or 'Not supplied by provider'
    stores_total=len(data['stores'])
    stores_available=len({(r['Store ID'] or r['Store'],r['City'],r['State']) for r in rows})
    a,b,c=st.columns(3)
    a.metric('Stores with reported stock',stores_available)
    b.metric('Available configurations',len(rows))
    c.metric('Stores in feed',stores_total)
    st.caption(f'Provider timestamp: {timestamp} · Dashboard refresh: every 30 seconds while this page is open · Data may be cached for up to 25 seconds')
    with st.expander('Filters', expanded=True):
        x,y,z=st.columns([2,1,1])
        search=x.text_input('Search by store or city',placeholder='Search nationwide…')
        states=sorted({r['State'] for r in rows if r['State']})
        state=y.selectbox('State', ['All states']+states)
        storage=z.selectbox('Storage', ['All capacities']+sorted({r['Storage'] for r in rows if r['Storage']}))
    shown=[r for r in rows if (not search or search.lower() in (r['Store']+' '+r['City']).lower()) and (state=='All states' or r['State']==state) and (storage=='All capacities' or r['Storage']==storage)]
    if rows and not shown:
        st.warning('Inventory is reported elsewhere, but no configurations match these filters.')
    elif not rows:
        st.warning('The provider currently reports no available pickup configurations nationwide. This is not a guarantee of zero stock.')
    else:
        st.success(f'{len(shown)} matching pickup configurations')
        st.dataframe([{k:v for k,v in r.items() if k!='Store ID'} for r in shown],hide_index=True,use_container_width=True)
        st.link_button('Open Apple checkout', APPLE)
    if st.button('Refresh now',type='primary'):
        get_inventory.clear()
        st.rerun(scope='fragment')

inventory_panel()
st.divider()
st.markdown('**Data source:** [PickupChecker](https://pickupchecker.com/iphone-duo-stock-checker) · [Apple checkout](https://www.apple.com/shop/buy-iphone)')
st.caption('Not affiliated with Apple, Verizon, or PickupChecker. This dashboard does not collect Apple credentials, process purchases, or guarantee availability. Respect the inventory provider’s published API terms and rate limits before public deployment.')
