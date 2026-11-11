import streamlit as st
import pandas as pd
from engine import evaluate, REQUIRED
from pathlib import Path
from collector import validate
from audit import inspect_stored, inspect
from free_sources import (RANK_FIELDS,TREND_FIELDS,import_rank_snapshots,rank_summary,
                          import_search_interest,search_interest_summary)

st.set_page_config(page_title='Amazon Sustainable Demand Monitor V1.3',page_icon='📦',layout='wide')
st.title('📦 Amazon Sustainable Demand Monitor')
st.caption('V1.3 • Free-data research • UK & Ireland • No orders or purchases')
st.warning('No live Amazon API. Scheduled collection runs only when you configure an authorised CSV feed in GitHub Actions. Amazon sales volumes are NOT known. No purchase recommendations from rankings or search interest alone.')
with st.sidebar:
    st.header('Settings')
    budget=st.slider('Reselling budget (€)',500,1000,750,50)
    markets=st.multiselect('Market', ['UK','IE'],default=['UK','IE'])
    st.caption('All monetary inputs in EUR. UK prices must be converted consistently before upload. A checked box or verified=true is not independent verification.')

def download_template(label,fields,filename,example):
    st.download_button(label,pd.DataFrame([example]).reindex(columns=fields).to_csv(index=False),filename,'text/csv')

t1,t2,t3,t4,t5,t6=st.tabs(['12-month research','Amazon rank snapshots','External search interest','Stored observations','Data readiness','Method & safeguards'])
with t1:
    st.subheader('Historical product research')
    st.write('Upload monthly research observations from a source you are permitted to use. The demand_index must be a consistent, documented 0–100 proxy. It is NOT units sold.')
    example={k:('UK' if k=='market' else 'B000EXAMPLE' if k=='asin' else 'Example product' if k=='product' else '2026-01' if k=='month' else 'Documented source URL and methodology' if k=='source' else False if k=='verified' else 50 if k in ['demand_index','competition_index'] else 0) for k in REQUIRED}
    download_template('Download monthly research CSV template',REQUIRED,'monthly_research_template.csv',example)
    file=st.file_uploader('Monthly research CSV',type=['csv'],key='monthly')
    stored=Path('data/monthly.csv')
    if file or stored.exists():
        try:
            df=pd.read_csv(file) if file else pd.read_csv(stored)
            if not file: st.caption('Using repository-stored research observations; data is not independently verified.')
            result=evaluate(df,budget)
            if not result.empty:
                result=result[result.market.isin(markets)]
                st.metric('Products assessed',len(result))
                st.dataframe(result,use_container_width=True,hide_index=True)
                st.download_button('Export assessments',result.to_csv(index=False),'amazon_v1_1_assessments.csv','text/csv')
                st.caption('TEST PURCHASE CANDIDATE is a heuristic screen, not a verified investment recommendation. Confirm fees, restrictions, VAT, supplier and demand before buying.')
            else:st.info('No usable observations in this upload.')
        except Exception as exc:st.error(f'Could not analyse research: {exc}')
    else:st.info('No research uploaded. No product recommendations available.')
with t2:
    st.subheader('Amazon bestseller-rank observations')
    st.write('Upload manually recorded, dated public category-rank snapshots. Ranks from different categories are not directly comparable. A rank is NOT a sale count. This tab never issues a purchase recommendation.')
    download_template('Download rank snapshot CSV template',RANK_FIELDS,'rank_snapshot_template.csv',{'market':'UK','asin':'B000EXAMPLE','product':'Example product','observed_at':'2026-11-01','best_seller_rank':250,'category':'Home & Kitchen','source_url':'https://www.amazon.co.uk/'})
    file=st.file_uploader('Rank snapshots CSV',type=['csv'],key='rank')
    stored=Path('data/ranks.csv')
    if file or stored.exists():
        try:
            d=import_rank_snapshots(file if file else stored)
            if not file: st.caption('Using repository-stored rank observations.')
            summary=rank_summary(d)
            if not summary.empty:
                st.dataframe(summary[summary.market.isin(markets)],use_container_width=True,hide_index=True)
                st.download_button('Export rank research',summary.to_csv(index=False),'rank_research.csv','text/csv')
            else:st.info('No valid rank observations.')
        except Exception as exc:st.error(f'Invalid rank file: {exc}')
with t3:
    st.subheader('Optional external search-interest research')
    st.write('Upload monthly 0–100 relative interest observations (for example, from an authorised manual Google Trends export). Search interest is not Amazon demand or actual purchases. UK and Ireland must be researched separately.')
    download_template('Download search interest CSV template',TREND_FIELDS,'search_interest_template.csv',{'market':'IE','keyword':'drawer organiser','month':'2026-01','search_interest':50,'source':'Manual Google Trends export, Ireland'})
    file=st.file_uploader('Search-interest CSV',type=['csv'],key='interest')
    stored=Path('data/interest.csv')
    if file or stored.exists():
        try:
            d=import_search_interest(file if file else stored)
            if not file: st.caption('Using repository-stored search-interest observations.')
            summary=search_interest_summary(d)
            if not summary.empty:
                st.dataframe(summary[summary.market.isin(markets)],use_container_width=True,hide_index=True)
                st.download_button('Export search interest',summary.to_csv(index=False),'search_interest_research.csv','text/csv')
            else:st.info('No valid search-interest observations.')
        except Exception as exc:st.error(f'Invalid interest file: {exc}')
with t4:
    st.subheader('Repository-backed observation history')
    st.write('GitHub Actions can collect authorised CSV feeds weekly and commit validated observations to the repository. Render then reads the committed files after redeployment. No feeds are configured by default.')
    for kind, filename in [('Monthly research','monthly.csv'),('Amazon rank snapshots','ranks.csv'),('External search interest','interest.csv')]:
        path=Path('data')/filename
        if path.exists():
            try:
                d=pd.read_csv(path)
                st.write(f'**{kind}:** {len(d)} stored rows')
                st.download_button(f'Download stored {kind.lower()}',path.read_bytes(),filename,'text/csv',key=filename)
            except Exception as exc: st.error(f'Cannot read {filename}: {exc}')
        else: st.info(f'{kind}: no stored feed yet')
    st.caption('Scheduled runs do not manufacture historical observations. An authorised source must supply each dated record.')
with t5:
    st.subheader('Data readiness and coverage audit')
    st.write('This page verifies what is actually stored. It does not retrieve Amazon sales or claim a feed is configured.')
    overview,details=inspect_stored()
    st.dataframe(overview,use_container_width=True,hide_index=True)
    if 'monthly' in details and 'coverage' in details['monthly']:
        st.write('**12-month coverage by product and marketplace**')
        coverage=details['monthly']['coverage']
        st.dataframe(coverage,use_container_width=True,hide_index=True)
        st.download_button('Download coverage audit',coverage.to_csv(index=False),'coverage_audit.csv','text/csv')
        st.caption('Complete 12-month coverage means 12 observed months, not verified sales or reliable forecasts.')
    for kind,info in details.items():
        if 'error' in info: st.error(f'{kind}: {info["error"]}')
    st.info('To populate this audit, upload legitimately obtained observations or configure an authorised CSV feed in GitHub Actions. Without a feed, scheduled jobs collect nothing.')
with t6:
    st.subheader('What V1.3 does and does not do')
    st.markdown('''- **Free and offline:** accepts user-provided CSV research; no API key or recurring data subscription.\n- **No scraping:** does not fetch Amazon pages, bypass access controls, or claim unauthorised API access.\n- **No backfilled history:** if you start recording ranks today, it takes 12 months to accumulate 12 months of genuine monthly observations unless you already have lawful historical data.\n- **No actual unit sales:** Amazon bestseller rank and search-interest indices are proxies.\n- **No automatic market mapping:** Amazon UK and Ireland are separate markets.\n- **No live supplier verification:** `verified=true` is an operator assertion; verify independently.\n- **No purchases:** recommendations are research screens only.\n- **Storage:** GitHub-committed CSV files persist across Render restarts; uploaded files remain temporary unless separately committed. Do not commit private data to a public repository.\n- **Costs:** all monetary data in EUR; consider FX, VAT, marketplace fees, returns, import duties and compliance before investing.''')
