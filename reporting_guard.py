"""Strict, minimized reporting boundary. Never echo stored free text."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from commercial_privacy import asin
from persistent_store import secure_storage_enabled
import os

MAX_RECORDS = 10000
class ReportError(ValueError):
    pass

def require(ok):
    if not ok:
        raise ReportError('Invalid or incomplete commercial reporting evidence.')

def bounded(rows, limit=MAX_RECORDS):
    require(isinstance(rows, (list, tuple)) and len(rows)<limit)
    require(all(isinstance(r, dict) for r in rows))
    return rows

def key(row):
    try:
        product=asin(row.get('asin'))
    except ValueError:
        raise ReportError('Invalid product identifier.') from None
    market=row.get('marketplace')
    require(market in ('UK','IE'))
    return product,market

def timestamp(value, now):
    try:
        require(isinstance(value,(str,datetime)))
        at=value if isinstance(value,datetime) else datetime.fromisoformat(value.replace('Z','+00:00'))
        require(at.tzinfo is not None and at.utcoffset() is not None)
        at=at.astimezone(timezone.utc)
        require(at<=now)
        return at
    except (ValueError,TypeError,OverflowError):
        raise ReportError('Invalid or future observation timestamp.') from None

def number(value, low, high):
    require(type(value) in (str,int,float,Decimal) and len(str(value))<=64)
    try:
        n=Decimal(str(value))
        require(n.is_finite() and low<=n<=high)
        return n
    except (InvalidOperation,ValueError):
        raise ReportError('Invalid commercial numeric evidence.') from None

def scenario(row):
    p,c,ref,ful,inc,other,ret=[number(row.get(k),0,100 if k.endswith('_pct') else 1000000) for k in ('selling_price_eur','supplier_cost_eur','referral_pct','fulfilment_eur','inbound_eur','other_eur','returns_pct')]
    profit=p-c-p*ref/100-ful-inc-other-p*ret/100
    roi=profit/c*100 if c else None
    # Extremely small costs can produce misleading or nonportable ratios.
    if roi is not None: require(abs(roi)<=Decimal('1e12'))
    return float(p),float(round(profit,2)),None if roi is None else float(round(roi,2))

def projected(row):
    product,market=key(row)
    profit=row.get('scenario_profit_eur'); roi=row.get('scenario_roi_pct')
    profit=None if profit is None else float(number(profit,-6000000,1000000))
    roi=None if roi is None else float(number(roi,-10**12,10**12))
    return {'asin':product,'marketplace':market,'name':'Product '+product,
            'scenario_profit_eur':profit,'scenario_roi_pct':roi,
            'research_priority':'REVIEW SCENARIO' if profit is not None and profit>0 and roi is not None and roi>=30 else 'INSUFFICIENT OR LOW SCENARIO',
            'buy_recommendation':False}

def reader_url(explicit=None):
    if secure_storage_enabled(): return None
    url=explicit or os.getenv('DATABASE_URL','')
    require(bool(url))
    return url
