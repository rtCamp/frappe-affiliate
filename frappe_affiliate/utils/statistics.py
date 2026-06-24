from collections import defaultdict

import frappe
from frappe.utils import flt, get_datetime, getdate


def fetch_referral_and_click_buckets(sales_partner, range_start, range_end):
    """Bulk-fetch referral/void and click rows for [range_start, range_end], bucketed by date.

    Single source of truth for the bulk statistics paths in both affiliate_statistics
    (monthly/daily) and affiliate_advanced_statistics (grouped). Resolve the Sales Partner
    in the caller and pass it in; aggregate each period from the returned buckets with
    aggregate_period().

    Returns (referrals_by_date, clicks_by_date):
        referrals_by_date[date] = {
            "referral": [amount, ...],             # every referral row, incl. voided ones
            "void":     [amount, ...],             # void records (deductions)
        }
        clicks_by_date[date] = [remote_address, ...]
    """
    referrals_by_date = defaultdict(lambda: {"referral": [], "void": []})
    clicks_by_date = defaultdict(list)

    if not sales_partner:
        return referrals_by_date, clicks_by_date

    start_datetime = get_datetime(range_start)
    end_datetime = get_datetime(range_end).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    # No void filter: voided referrals must stay in as positive entries so the void records
    # (subtracted in aggregate_period) net them out — a partial void only removes the
    # returned fraction, leaving the remaining fee intact.
    for r in frappe.get_all(
        "Affiliate Referral",
        filters={
            "sales_partner": sales_partner,
            "record_type": ["in", ["referral", "void"]],
            "date": ["between", [range_start, range_end]],
        },
        fields=["date", "amount", "record_type"],
    ):
        referrals_by_date[r.date][r.record_type].append(r.amount)

    for c in frappe.get_all(
        "Affiliate Click Log",
        filters={
            "sales_partner": sales_partner,
            "time": ["between", [start_datetime, end_datetime]],
        },
        fields=["time", "remote_address"],
    ):
        clicks_by_date[getdate(c.time)].append(c.remote_address)

    return referrals_by_date, clicks_by_date


def aggregate_period(referrals_by_date, clicks_by_date, period_start, period_end):
    """Aggregate one period's stats from the buckets produced by fetch_referral_and_click_buckets.

    Single source of truth for the void / transaction / click rules (no DB queries):
      - referral_fee_earned = sum(all referral amounts) - sum(void amounts), rounded to
        2 decimal places. Voided referrals stay positive; the void record carries the
        keeps its remaining fee.
      - transactions = count of all referrals (a referral that earned commission counts
        even if later voided); the void's earnings impact is still netted above.
      - unique_clicks unions IPs across every date in the period (correct cross-day dedup;
        a per-day SQL DISTINCT summed across days would overcount multi-day periods).
    """
    period_dates = [d for d in referrals_by_date if period_start <= d <= period_end]
    sales = [a for d in period_dates for a in referrals_by_date[d]["referral"]]
    void_amounts = [a for d in period_dates for a in referrals_by_date[d]["void"]]

    click_dates = [d for d in clicks_by_date if period_start <= d <= period_end]
    clicks_count = sum(len(clicks_by_date[d]) for d in click_dates)
    unique_clicks = len({ip for d in click_dates for ip in clicks_by_date[d]})

    return {
        "transactions": len(sales),
        "referral_fee_earned": flt(sum(sales) - sum(void_amounts), 2),
        "clicks": clicks_count,
        "unique_clicks": unique_clicks,
    }
