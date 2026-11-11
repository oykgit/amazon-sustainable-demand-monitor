"""Research-only EUR profitability scenarios. Inputs are user supplied, never live Amazon fees."""
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def amount(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number")
    if not result.is_finite() or result < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return result


def pct(value, label):
    v = amount(value, label)
    if v > 100:
        raise ValueError(f"{label} cannot exceed 100%")
    return v / 100


def money(v):
    return float(v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calculate(*, price, unit_cost, referral_pct, fulfilment_fee, inbound_shipping,
              packaging, other_cost, return_reserve_pct, vat_rate_pct,
              vat_included, vat_recoverable, referral_on_gross=True):
    """Simplified unit economics, all amounts in EUR.

    vat_rate_pct is a user-supplied scenario rate, NOT an official tax determination.
    vat_recoverable applies only to VAT in the unit purchase cost, assuming the user
    has entered a VAT-inclusive cost at the same scenario rate. No other input VAT is modelled.
    """
    p=amount(price,'Selling price'); c=amount(unit_cost,'Unit purchase cost')
    referral=pct(referral_pct,'Referral fee rate'); returns=pct(return_reserve_pct,'Returns reserve')
    vat=pct(vat_rate_pct,'VAT rate')
    f=amount(fulfilment_fee,'Fulfilment fee'); s=amount(inbound_shipping,'Inbound shipping')
    pack=amount(packaging,'Packaging'); other=amount(other_cost,'Other costs')
    if p == 0: raise ValueError('Selling price must be greater than zero')
    net_revenue = p/(1+vat) if vat_included else p
    output_vat = p-net_revenue if vat_included else Decimal(0)
    cost_net = c/(1+vat) if vat_recoverable else c
    recovered_input_vat = c-cost_net
    referral_base = p if referral_on_gross else net_revenue
    fee = referral_base*referral
    return_reserve = p*returns
    total_cost = cost_net+fee+f+s+pack+other+return_reserve
    profit = net_revenue-total_cost
    roi = profit/cost_net*100 if cost_net > 0 else None
    margin = profit/net_revenue*100 if net_revenue > 0 else None
    # Linear cost model: return reserve and referral fee scale with price.
    revenue_factor = (1/(1+vat)) if vat_included else Decimal(1)
    referral_factor = referral if referral_on_gross else referral*revenue_factor
    denominator = revenue_factor-referral_factor-returns
    fixed = cost_net+f+s+pack+other
    break_even = fixed/denominator if denominator > 0 else None
    return {
        'selling_price_eur': money(p), 'net_sales_revenue_eur': money(net_revenue),
        'scenario_output_vat_eur': money(output_vat),
        'scenario_recoverable_purchase_vat_eur': money(recovered_input_vat),
        'purchase_cost_used_eur': money(cost_net), 'referral_fee_eur': money(fee),
        'fulfilment_fee_eur': money(f), 'inbound_shipping_eur': money(s),
        'packaging_eur': money(pack), 'other_cost_eur': money(other),
        'returns_reserve_eur': money(return_reserve),
        'total_modelled_cost_eur': money(total_cost), 'net_profit_eur': money(profit),
        'profit_margin_pct': round(float(margin),2) if margin is not None else None,
        'roi_on_purchase_cost_pct': round(float(roi),2) if roi is not None else None,
        'break_even_price_eur': money(break_even) if break_even is not None else None,
        'break_even_possible': break_even is not None,
        'data_status':'USER-ENTERED SCENARIO — NOT VERIFIED AMAZON FEES OR TAX ADVICE'
    }


def screen(result, min_profit, min_roi):
    profit = result['net_profit_eur']
    roi = result['roi_on_purchase_cost_pct']
    if profit < float(min_profit) or roi is None or roi < float(min_roi):
        return 'BELOW SCENARIO THRESHOLD'
    return 'PASSES SCENARIO THRESHOLD — NOT A BUY RECOMMENDATION'
