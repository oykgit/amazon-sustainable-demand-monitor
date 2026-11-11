import streamlit as st
import pandas as pd
from engine import evaluate, REQUIRED

st.set_page_config(page_title='Amazon Sustainable Demand Monitor',page_icon='📦',layout='wide')
st.title('📦 Amazon Sustainable Demand Monitor')
st.caption('V1.0 • UK & Ireland • Research-only • No orders or purchases')
st.warning('No live Amazon connection in V1.0. Upload your own legitimately obtained market observations. Scores are heuristic, not verified sales forecasts.')
with st.sidebar:
    st.header('Settings')
    budget=st.slider('Reselling budget (€)',500,1000,750,50)
    market=st.multiselect('Market', ['UK','IE'],default=['UK','IE'])
    st.markdown('**Data rules:** 12 monthly observations per product; verified source and costs required for test-purchase status.')
st.subheader('Import market research')
st.write('Upload a CSV with one row per product per month. Download the template to see the required fields. `demand_index` is a consistent 0–100 proxy, not actual units sold. `competition_index` is 0–100, higher meaning more competitive. Set `verified=true` only when source and cost data have been checked.')
template=pd.DataFrame([{k:('UK' if k=='market' else 'B000EXAMPLE' if k=='asin' else 'Example product' if k=='product' else '2026-01' if k=='month' else 'Research provider' if k=='source' else 'false' if k=='verified' else 50 if k in ['demand_index','competition_index'] else 0) for k in REQUIRED}])
st.download_button('Download CSV template',template.to_csv(index=False),'amazon_monitor_template.csv','text/csv')
upload=st.file_uploader('Upload observations CSV',type=['csv'])
if upload is None:
    st.info('Waiting for historical market observations. No products are recommended until valid data is uploaded.')
    st.stop()
try:
    df=pd.read_csv(upload)
    results=evaluate(df,budget)
except Exception as e:
    st.error(f'Unable to process file: {e}')
    st.stop()
if results.empty:
    st.warning('No usable product observations found.')
    st.stop()
results=results[results.market.isin(market)]
a,b,c=st.columns(3)
a.metric('Products evaluated',len(results))
b.metric('Test-purchase candidates',int((results.decision=='TEST PURCHASE CANDIDATE').sum()))
c.metric('Needs research',int((results.decision=='RESEARCH REQUIRED').sum()))
st.subheader('Product recommendations')
st.dataframe(results,use_container_width=True,hide_index=True)
st.download_button('Export recommendations CSV',results.to_csv(index=False),'recommendations.csv','text/csv')
selected=st.selectbox('Inspect product',results['asin'].tolist(),format_func=lambda x:results.loc[results.asin==x,'product'].iloc[0])
g=df[df.asin==selected].copy();g['month']=pd.to_datetime(g['month'],errors='coerce');g=g.sort_values('month')
if not g.empty:
    st.subheader('Historical observations')
    st.line_chart(g.set_index('month')[['demand_index']])
    st.line_chart(g.set_index('month')[['sale_price']])
st.caption('Before spending money: verify marketplace seller eligibility, brand restrictions, VAT, import obligations, product safety, landed costs and supplier authenticity. No score guarantees demand or profit.')
