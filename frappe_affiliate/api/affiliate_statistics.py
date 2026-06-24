import frappe
from frappe import _
from frappe.utils import (
    add_months,
    cint,
    formatdate,
    get_datetime,
    get_first_day,
    get_last_day,
    getdate,
)

from frappe_affiliate.utils.statistics import (
    aggregate_period,
    fetch_referral_and_click_buckets,
)


@frappe.whitelist()
def get_affiliate_statistics(
    by_month: int = 0, month: str | None = None, start: int = 0, limit: int = 20
):
    affiliate_join = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "creation"
    )

    by_month = cint(by_month)
    start = cint(start)
    limit = cint(limit)

    if not affiliate_join:
        return {"error": "No affiliate record found for current user"}

    if by_month and month:
        return get_daily_statistics(month)
    else:
        # The start and limit parameters are based on months and only used when not by_month (monthly statistics pagination)
        return get_monthly_statistics(affiliate_join, start, limit)


def get_monthly_statistics(affiliate_join, start, limit):
    """Get affiliate statistics grouped by month"""
    current_date = getdate()
    affiliate_join_date = get_datetime(affiliate_join)
    affiliate_join_date = (
        get_first_day(affiliate_join_date)
        if affiliate_join_date
        else get_first_day(current_date)
    )

    start_date = add_months(current_date, -start)
    end_date = add_months(start_date, -limit + 1)

    if end_date < affiliate_join_date:
        end_date = affiliate_join_date
    if start_date < affiliate_join_date:
        start_date = affiliate_join_date

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )
    # Fetch the whole window once and aggregate each month in memory to avoid per-month
    # queries. get_period_statistics remains the standalone single-period version.
    referrals_by_date, clicks_by_date = fetch_referral_and_click_buckets(
        sales_partner, get_first_day(end_date), get_last_day(start_date)
    )

    monthly_data = []

    total_dict = {
        "transactions": 0,
        "referral_fee_earned": 0.0,
        "clicks": 0,
        "unique_clicks": 0,
    }

    current_month = start_date
    while current_month >= end_date:
        month_start = get_first_day(current_month)
        month_end = get_last_day(current_month)

        stats = aggregate_period(
            referrals_by_date, clicks_by_date, month_start, month_end
        )
        stats["period"] = formatdate(month_start, "yyyy-MM")
        stats["period_label"] = formatdate(month_start, "MMMM yyyy")

        monthly_data.append(stats)

        for key, value in total_dict.items():
            total_dict[key] = value + stats[key]

        current_month = add_months(current_month, -1)

    data = {
        "data": monthly_data,
        "values_total": total_dict,
        "start": start,
        "limit": limit,
        "total": max(
            (current_date.year - affiliate_join_date.year) * 12
            + (current_date.month - affiliate_join_date.month),
            len(monthly_data),
        ),
    }
    return data


def get_daily_statistics(month):
    """Get affiliate statistics grouped by day for a specific month"""

    try:
        # Parse month (expected format: YYYY-MM)
        month_parts = month.split("-")
        year, month_num = [int(part) for part in month_parts]
        month_date = getdate(f"{year}-{month_num:02d}-01")

        month_start = get_first_day(month_date)
        month_end = get_last_day(month_date)

    except (ValueError, AttributeError):
        return {"error": "Invalid month format. Use YYYY-MM"}

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )
    # Fetch the whole month once and aggregate each day in memory to avoid per-day queries.
    referrals_by_date, clicks_by_date = fetch_referral_and_click_buckets(
        sales_partner, month_start, month_end
    )

    daily_data = []

    total_dict = {
        "transactions": 0,
        "referral_fee_earned": 0.0,
        "clicks": 0,
        "unique_clicks": 0,
    }

    current_day = month_start
    while current_day <= month_end:
        stats = aggregate_period(
            referrals_by_date, clicks_by_date, current_day, current_day
        )
        stats["period"] = formatdate(current_day, "yyyy-MM-dd")
        stats["period_label"] = formatdate(current_day, "MMMM dd, yyyy")

        daily_data.append(stats)

        for key, value in total_dict.items():
            total_dict[key] = value + stats[key]

        current_day = frappe.utils.add_days(current_day, 1)

    data = {
        "data": daily_data,
        "values_total": total_dict,
        "total": len(daily_data),
    }
    return data


def get_period_statistics(start_date, end_date):
    """Get affiliate statistics for a specific period.

    Standalone single-period helper kept for external callers. Delegates to the shared
    bulk helpers so the void / transaction / click rules live in one place.
    """
    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )

    if not sales_partner:
        return {
            "transactions": 0,
            "referral_fee_earned": 0.0,
            "clicks": 0,
            "unique_clicks": 0,
        }

    period_start = getdate(start_date)
    period_end = getdate(end_date)
    referrals_by_date, clicks_by_date = fetch_referral_and_click_buckets(
        sales_partner, period_start, period_end
    )
    return aggregate_period(referrals_by_date, clicks_by_date, period_start, period_end)


@frappe.whitelist(methods=["GET"])
def get_click_log_for_statistic(
    date: str | None = None, by_month: int = 1, start: int = 0, limit: int = 20
) -> dict:
    """
    Get click log entries for a specific date

    Params:
    - date (str): The date or month for which to retrieve click logs.
    - by_month (int): If 1, date is treated as month (YYYY-MM); if 0, as specific date (YYYY-MM-DD).
    - start (int): The starting index for pagination.
    - limit (int): The number of records to retrieve.

    Response:
        {
        "message": {
            "click_logs": [
                {
                    "time": "2025-11-25 10:52:27",
                    "referrer": null
                },
                {
                    "time": "2025-11-25 10:52:27",
                    "referrer": "https://www.google.com"
                }
            ],
            "total": 2,
            "start": 0,
            "limit": 20
        }
    }
    """
    by_month = cint(by_month)
    limit = max(1, cint(limit))
    start = max(0, cint(start))

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )

    result = {
        "click_logs": [],
        "total": 0,
        "start": start,
        "limit": limit,
    }

    if not sales_partner:
        return result

    try:
        if by_month:
            modified_date = date + "-01"
            start_date = get_first_day(modified_date)
            end_date = get_last_day(start_date)
        else:
            start_date = end_date = getdate(date)
    except (ValueError, AttributeError, TypeError):
        frappe.throw(_("Invalid date format."))

    start_datetime = frappe.utils.get_datetime(start_date)
    end_datetime = frappe.utils.get_datetime(end_date).replace(
        hour=23, minute=59, second=59
    )

    filters = {
        "sales_partner": sales_partner,
        "time": ["between", [start_datetime, end_datetime]],
    }

    click_logs = frappe.get_all(
        "Affiliate Click Log",
        filters=filters,
        order_by="time desc",
        fields=["time", "referrer"],
        start=start,
        limit=limit,
    )

    total_clicks = frappe.db.count(
        "Affiliate Click Log",
        filters=filters,
    )

    result["click_logs"] = click_logs
    result["total"] = total_clicks

    return result
