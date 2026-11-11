import streamlit as st
import pandas as pd
from engine import evaluate, REQUIRED
from demand_history import analyse_history
from profitability import calculate, screen
from competition import assess_competition, REQUIRED_COMPETITION
from pathlib import Path
from collector import validate
from audit import inspect_stored, inspect
from product_catalogue import lookup_barcode
from catalogue_sources import lookup_product, observation, merge_observations, FIELDS, validate_barcode
from api_diagnostics import check_provider, CatalogueConnectionError
from provider_guard import ProviderGuard
from free_sources import (RANK_FIELDS,TREND_FIELDS,import_rank_snapshots,rank_summary,
                          import_search_interest,search_interest_summary)

st.set_page_config(page_title='Amazon Sustainable Demand Monitor V1.8.2',page_icon='📦',layout='wide')
st.title('📦 Amazon Sustainable Demand Monitor')
st.caption('V1.8.2 • demand intelligence & profitability scenarios • UK & Ireland • No orders or purchases')
st.warning('No live Amazon API. Free catalogue lookups do not establish Amazon sales or prices. Scheduled collection runs only when you configure an authorised CSV feed in GitHub Actions. Amazon sales volumes are NOT known. No purchase recommendations from rankings or search interest alone.')
NAVIGATION = [
    'Overview', '12-month research', 'Amazon rank snapshots', 'External search interest',
    'Stored observations', 'Data readiness', 'Product catalogue', 'Free data integration', 'Demand intelligence',
    'Profitability scenarios', 'Competition analysis', 'Method & safeguards'
]
with st.sidebar:
    st.header('Navigation')
    page = st.radio('Choose a workspace', NAVIGATION, label_visibility='collapsed')
    st.divider()
    st.subheader('Research settings')
    budget = st.slider('Reselling budget (€)', 500, 1000, 750, 50)
    markets = st.multiselect('Market', ['UK', 'IE'], default=['UK', 'IE'])
    st.caption('Amounts are EUR. UK prices require documented conversion. Data marked verified by an operator is not independently verified.')

if page == 'Overview':
    st.subheader('Research overview')
    st.info('Research-only dashboard. No verified Amazon unit sales, product buy recommendations, or purchasing integration.')
    overview, details = inspect_stored()
    monthly_path = Path('data/monthly.csv')
    product_count = 0
    if monthly_path.exists():
        try:
            monthly = pd.read_csv(monthly_path)
            if {'market','asin'}.issubset(monthly.columns):
                product_count = len(monthly[monthly.market.isin(markets)][['market','asin']].drop_duplicates())
        except Exception:
            st.warning('Monthly data could not be read; use Data readiness for details.')
    a,b,c = st.columns(3)
    a.metric('Products with stored research', product_count)
    b.metric('Research budget', f'€{budget:,}')
    c.metric('Verified Amazon sales feed', 'Not connected')
    st.write('**Stored data readiness**')
    st.dataframe(overview, use_container_width=True, hide_index=True)
    st.caption('Use the sidebar to open a research workspace. All profitability and competition results are scenario assessments, not verified investment opportunities.')

def download_template(label,fields,filename,example):
    st.download_button(label,pd.DataFrame([example]).reindex(columns=fields).to_csv(index=False),filename,'text/csv')


if page == '12-month research':
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
if page == 'Amazon rank snapshots':
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
if page == 'External search interest':
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
if page == 'Stored observations':
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
if page == 'Data readiness':
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
if page == 'Product catalogue':
    st.subheader('Live product identification (free, optional)')
    st.write('Look up a food product by barcode using the public Open Food Facts catalogue. This supplies real product identity information, **not Amazon UK or Ireland sales, prices, bestseller ranks, or resale eligibility**. No product is recommended for purchase from this lookup.')
    barcode=st.text_input('Product barcode (8–14 digits)',placeholder='e.g. barcode printed on packaging')
    if st.button('Look up product',type='primary'):
        try:
            result=lookup_barcode(barcode)
            if result['found']:
                st.success('Product record found in Open Food Facts')
                st.write('**Name:**',result['name'] or 'Not provided')
                st.write('**Brand:**',result['brand'] or 'Not provided')
                st.write('**Quantity:**',result['quantity'] or 'Not provided')
            else:st.info('No catalogue record found for this barcode.')
            st.link_button('View source record',result['source_url'])
            st.warning('Amazon sales, selling price, fees, product restrictions and 12-month demand are NOT verified by this source.')
        except Exception as exc:st.error(f'Catalogue lookup unavailable: {exc}')
    st.caption('Source: Open Food Facts community-maintained data. Product coverage and correctness vary. Data may be subject to Open Database License obligations; check terms before reuse.')
if page == 'Free data integration':
    st.subheader('Free data integration centre')
    st.caption('V1.8.2: session-scoped cache, provider cooldowns and request log. These controls do not bypass access restrictions.')
    if 'provider_guard' not in st.session_state:
        st.session_state.provider_guard = ProviderGuard()
    guard = st.session_state.provider_guard
    for provider_name in ['Open Food Facts', 'UPCitemdb']:
        remaining = guard.remaining(provider_name)
        st.caption(f'{provider_name}: ' + (f'cooldown active ({remaining} seconds remaining)' if remaining else 'no local cooldown'))
    if st.button('Run connection diagnostics (both providers)', key='v182_diagnostics'):
        for provider in ['Open Food Facts', 'UPCitemdb']:
            if guard.remaining(provider):
                st.warning(f'{provider}: diagnostics skipped during cooldown; no request sent.')
                continue
            diagnostic = check_provider(provider)
            st.write(diagnostic['provider'], diagnostic)
            if not diagnostic['reachable']:
                if diagnostic.get('http_status') in (403, 429):
                    error = CatalogueConnectionError(provider, diagnostic['http_status'],
                                                     diagnostic['message'], diagnostic.get('retry_after'))
                    guard.record_error(provider, error)
                st.warning('Provider denied or could not complete the request. Browser access does not guarantee server access.')
            else:
                guard._log(provider, 'diagnostic_success', 200)
    if guard.events:
        with st.expander('Recent API request events (this session only)'):
            st.dataframe(pd.DataFrame(guard.events[-30:]), hide_index=True)
    st.info('Live barcode identity lookups are available on demand. Neither provider supplies Amazon prices, sales, rankings or resale eligibility. No paid credentials required.')
    st.write('**Sources:** [UPCitemdb](https://www.upcitemdb.com/api) (general retail catalogue, public trial endpoint) and [Open Food Facts](https://world.openfoodfacts.org/) (primarily foods). Provider rate limits, coverage and terms apply. UPCitemdb free usage can change.')
    source=st.selectbox('Catalogue provider', ['UPCitemdb','Open Food Facts'])
    code=st.text_input('Barcode (8–14 digits)',key='v18_code')
    if 'catalogue_observations' not in st.session_state:
        st.session_state.catalogue_observations=[]
    if st.button('Fetch live product metadata',type='primary'):
        try:
            result, result_origin=guard.fetch(source, validate_barcode(code), lookup_product)
            if result['found']:
                st.session_state.catalogue_observations.append(observation(result))
                st.success(f'Product metadata found ({result_origin}) and added to this session’s export list.')
            else:
                st.info('No exact matching barcode record was returned.')
            st.session_state.last_catalogue_result=result
        except Exception as exc:
            if isinstance(exc, CatalogueConnectionError):
                st.error(str(exc))
                if exc.retry_after: st.info(f'Provider Retry-After: {exc.retry_after}')
                if exc.status == 403: st.info('The provider denied this request from Render. This may require provider support or an approved alternative source; it is not necessarily a barcode problem.')
            else: st.error(f'Lookup failed: {type(exc).__name__}: {exc}')
    result=st.session_state.get('last_catalogue_result')
    if result:
        st.write('**Last result:**',{'source':result['source'],'barcode':result['barcode'],
                                     'found':result['found'],'name':result.get('name',''),
                                     'brand':result.get('brand','')})
        st.markdown(f"[Open provider record]({result['source_url']})")
    st.divider()
    st.write('**Exportable dated catalogue observations**')
    st.warning('Session records are temporary on Render. Download the CSV and commit it to `data/catalogue_observations.csv` in GitHub for persistence. Uploading or viewing a CSV does not automatically save it to GitHub.')
    uploaded=st.file_uploader('Optional: merge a previous catalogue observations CSV',type=['csv'],key='v18_merge')
    try:
        base=pd.read_csv(uploaded) if uploaded is not None else pd.DataFrame(columns=FIELDS)
        if not set(FIELDS).issubset(base.columns):
            raise ValueError('Uploaded file does not match the V1.8 catalogue observation format.')
        merged=base[FIELDS].copy()
        for record in st.session_state.catalogue_observations:
            merged=merge_observations(merged,record)
        st.metric('Exportable catalogue observations',len(merged))
        if not merged.empty:
            st.dataframe(merged,use_container_width=True,hide_index=True)
        st.download_button('Download observations CSV',merged.to_csv(index=False),
                           'catalogue_observations.csv','text/csv',key='v18_export')
    except Exception as exc:
        st.error(f'Could not merge observations: {exc}')
    stored_catalogue=Path('data/catalogue_observations.csv')
    if stored_catalogue.exists():
        try:
            saved=pd.read_csv(stored_catalogue)
            st.caption(f'Repository-stored catalogue observations: {len(saved)} rows. Download and merge this file before recording more observations.')
            st.download_button('Download repository catalogue CSV',stored_catalogue.read_bytes(),
                               'catalogue_observations.csv','text/csv',key='v18_stored')
        except Exception as exc:
            st.error(f'Could not read repository catalogue CSV: {exc}')
    st.caption('These records document product identities, not historical Amazon market prices or sales. Keepa adapter is a future integration, not connected in V1.8.')

if page == 'Demand intelligence':
    st.subheader('12-month demand intelligence (observed proxy data)')
    st.write('Measures completeness, variation and possible spikes in a documented 0–100 demand proxy. It cannot establish actual sales, annual seasonality or future demand.')
    history_file = st.file_uploader('Upload monthly research CSV for demand analysis', type=['csv'], key='demand_history')
    history_path = Path('data/monthly.csv')
    if history_file is not None or history_path.exists():
        try:
            observations = pd.read_csv(history_file if history_file is not None else history_path)
            analysed = analyse_history(observations)
            if not analysed.empty:
                analysed = analysed[analysed.market.isin(markets)]
                st.dataframe(analysed, use_container_width=True, hide_index=True)
                st.download_button('Download demand intelligence CSV', analysed.to_csv(index=False), 'v1_5_demand_intelligence.csv', 'text/csv')
                st.warning('All scores are descriptive proxy measures, not verified Amazon demand, unit sales or buying recommendations. One year cannot prove recurring annual seasonality.')
            else: st.info('No valid observations in the current 12-month window.')
        except Exception as exc: st.error(f'Could not analyse demand history: {exc}')
    else: st.info('Upload real observations or configure an authorised feed. No historical observations have been fabricated.')
if page == 'Method & safeguards':
    st.subheader('What V1.8 does and does not do')
    st.markdown('''- **Free research:** accepts user-provided CSV research and optionally queries Open Food Facts for live barcode metadata; no paid API key.\n- **No Amazon scraping:** does not fetch Amazon pages, bypass access controls, or claim unauthorised API access.\n- **No backfilled history:** if you start recording ranks today, it takes 12 months to accumulate 12 months of genuine monthly observations unless you already have lawful historical data.\n- **No actual unit sales:** Amazon bestseller rank and search-interest indices are proxies.\n- **No automatic market mapping:** Amazon UK and Ireland are separate markets.\n- **No live supplier verification:** `verified=true` is an operator assertion; verify independently.\n- **No purchases:** recommendations are research screens only.\n- **Storage:** GitHub-committed CSV files persist across Render restarts; uploaded files remain temporary unless separately committed. Do not commit private data to a public repository.\n- **Costs:** all monetary data in EUR; consider FX, VAT, marketplace fees, returns, import duties and compliance before investing.''')

if page == 'Profitability scenarios':
    st.subheader('V1.8 product profitability scenarios')
    st.warning('Research-only calculator. All fees, VAT treatment and costs are operator-entered assumptions, not live Amazon quotes. Do not treat a passing result as permission or advice to buy.')
    market=st.selectbox('Marketplace scenario', ['Amazon UK', 'Amazon Ireland'])
    st.caption('All figures must be in EUR. For UK GBP figures, convert externally using a documented exchange rate and account for currency conversion charges. Fees and tax treatment differ by seller, product, fulfilment and country.')
    left,right=st.columns(2)
    with left:
        price=st.number_input('Selling price (€)',min_value=0.01,value=24.99,step=0.50)
        cost=st.number_input('Unit purchase cost, VAT-inclusive if claiming input VAT (€)',min_value=0.0,value=9.00,step=0.50)
        referral=st.number_input('Referral fee assumption (%)',min_value=0.0,max_value=100.0,value=15.0,step=0.5)
        fulfil=st.number_input('Fulfilment or delivery fee per unit (€)',min_value=0.0,value=3.50,step=0.25)
        inbound=st.number_input('Inbound shipping per unit (€)',min_value=0.0,value=0.75,step=0.25)
        packaging=st.number_input('Packaging per unit (€)',min_value=0.0,value=0.25,step=0.25)
    with right:
        other=st.number_input('Other unit costs (€)',min_value=0.0,value=0.50,step=0.25)
        returns=st.number_input('Returns/refunds reserve (% of selling price)',min_value=0.0,max_value=100.0,value=3.0,step=0.5)
        vat_rate=st.number_input('Scenario VAT rate (%) — enter applicable rate',min_value=0.0,max_value=100.0,value=0.0,step=0.5)
        vat_included=st.checkbox('Selling price includes VAT that seller must remit',value=False)
        vat_recoverable=st.checkbox('Purchase cost includes recoverable input VAT at scenario rate',value=False)
        referral_gross=st.checkbox('Apply referral rate to VAT-inclusive selling price',value=True)
        min_profit=st.number_input('Minimum net profit per unit (€)',min_value=0.0,value=4.0,step=0.5)
        min_roi=st.number_input('Minimum ROI on purchase cost (%)',min_value=0.0,value=25.0,step=5.0)
    try:
        r=calculate(price=price,unit_cost=cost,referral_pct=referral,fulfilment_fee=fulfil,
                    inbound_shipping=inbound,packaging=packaging,other_cost=other,
                    return_reserve_pct=returns,vat_rate_pct=vat_rate,vat_included=vat_included,
                    vat_recoverable=vat_recoverable,referral_on_gross=referral_gross)
        a,b,c=st.columns(3)
        a.metric('Scenario net profit per unit',f"€{r['net_profit_eur']:.2f}")
        b.metric('Scenario ROI', 'N/A' if r['roi_on_purchase_cost_pct'] is None else f"{r['roi_on_purchase_cost_pct']:.2f}%")
        c.metric('Scenario break-even price','Not attainable' if r['break_even_price_eur'] is None else f"€{r['break_even_price_eur']:.2f}")
        st.write('**Scenario screening:**',screen(r,min_profit,min_roi))
        st.dataframe(pd.DataFrame([{'component':k,'value':v} for k,v in r.items()]),hide_index=True,use_container_width=True)
        export={'marketplace_scenario':market,**r,'threshold_status':screen(r,min_profit,min_roi)}
        st.download_button('Download profitability scenario CSV',pd.DataFrame([export]).to_csv(index=False),'v1_6_profitability_scenario.csv','text/csv')
        st.caption('Not modelled: seller plan subscription, storage, long-term storage, advertising, returns processing, category-specific fee rules, duties, tax obligations, FX spreads, and cash-flow timing unless included in Other costs. VAT calculation is simplified and may not reflect your legal treatment. Verify Amazon fees and tax with official sources before any transaction.')
    except ValueError as exc:
        st.error(str(exc))

if page == 'Competition analysis':
    st.subheader('Competition and market saturation research')
    st.warning('Manual, source-documented snapshots only. Seller counts and review counts are imperfect competition proxies; no live Amazon competitor data is connected.')
    st.write('Upload a CSV of competitor observations for the same product, marketplace and observation date. This is a descriptive screening tool, not a market-share or sales estimator.')
    example = {'market':'UK','asin':'B000EXAMPLE','observed_at':'2026-11-01','competing_listings':12,
               'median_competitor_price_eur':24.99,'median_review_count':130,
               'source':'Operator-recorded authorised research','notes':'Illustrative example only'}
    download_template('Download competition CSV template', REQUIRED_COMPETITION, 'competition_template.csv', example)
    uploaded = st.file_uploader('Competition observations CSV', type=['csv'], key='competition_csv')
    if uploaded is not None:
        try:
            observed = pd.read_csv(uploaded)
            result = assess_competition(observed)
            result = result[result.market.isin(markets)]
            if result.empty:
                st.info('No valid observations for the selected marketplaces.')
            else:
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.download_button('Download competition assessments', result.to_csv(index=False), 'v1_7_competition.csv', 'text/csv')
                st.caption('Screens indicate relative competition pressure from user-provided data only. They do not measure actual sales, Buy Box share, seller eligibility or total market size.')
        except (ValueError, KeyError) as exc:
            st.error(f'Invalid competition data: {exc}')
    else:
        st.info('No competition observations uploaded. No competition assessments available.')
