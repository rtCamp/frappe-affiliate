import frappe
from frappe.utils import (
    add_months,
    cint,
    formatdate,
    get_first_day,
    get_last_day,
    getdate,
)


@frappe.whitelist()
def get_affiliate_statistics(by_month=0, month=None):
    affiliate_join = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "creation"
    )

    by_month = cint(by_month)

    if not affiliate_join:
        return {"error": "No affiliate record found for current user"}

    if by_month and month:
        return get_daily_statistics(month)
    else:
        return get_monthly_statistics(affiliate_join)


def get_monthly_statistics(affiliate_join):
    """Get affiliate statistics grouped by month"""
    current_date = getdate()
    start_date = (
        get_first_day(affiliate_join) if affiliate_join else get_first_day(current_date)
    )

    monthly_data = []

    current_month = start_date
    while current_month <= current_date:
        month_start = get_first_day(current_month)
        month_end = get_last_day(current_month)

        stats = get_period_statistics(month_start, month_end)
        stats["period"] = formatdate(month_start, "yyyy-MM")
        stats["period_label"] = formatdate(month_start, "MMMM yyyy")

        monthly_data.append(stats)

        current_month = add_months(current_month, 1)

    return monthly_data


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

    daily_data = []

    current_day = month_start
    while current_day <= month_end:
        stats = get_period_statistics(current_day, current_day)
        stats["period"] = formatdate(current_day, "yyyy-MM-dd")
        stats["period_label"] = formatdate(current_day, "MMMM dd, yyyy")

        daily_data.append(stats)

        current_day = frappe.utils.add_days(current_day, 1)

    return daily_data


def get_period_statistics(start_date, end_date):
    """Get affiliate statistics for a specific period"""

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

    start_datetime = frappe.utils.get_datetime(start_date)
    end_datetime = frappe.utils.get_datetime(end_date).replace(
        hour=23, minute=59, second=59
    )

    sales = frappe.get_all(
        "Affiliate Referral",
        filters={
            "sales_partner": sales_partner,
            "record_type": "commission",
            "creation": ["between", [start_datetime, end_datetime]],
            "void": 0,
        },
        fields="amount",
        pluck="amount",
    )
    sales_count = len(sales)
    total_referral_fee = sum(sales)

    clicks_count = frappe.db.count(
        "Affiliate Click Log",
        filters={
            "sales_partner": sales_partner,
            "creation": ["between", [start_datetime, end_datetime]],
        },
    )
    unique_clicks_count = frappe.get_all(
        "Affiliate Click Log",
        filters={
            "sales_partner": sales_partner,
            "creation": ["between", [start_datetime, end_datetime]],
        },
        fields=["remote_address"],
        group_by="remote_address",
    )

    return {
        "transactions": sales_count,
        "referral_fee_earned": total_referral_fee,
        "clicks": clicks_count or 0,
        "unique_clicks": len(unique_clicks_count) or 0,
    }


@frappe.whitelist(methods=["GET"])
def get_click_log_for_statistic(
    date: str | None = None, by_month=1, start: int = 0, limit: int = 20
) -> list:
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
    },
    """
    by_month = cint(by_month)

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )

    if not sales_partner:
        return []

    try:
        if by_month:
            modified_date = date + "-01"
            start_date = get_first_day(modified_date)
            end_date = get_last_day(start_date)
        else:
            start_date = end_date = getdate(date)
    except (ValueError, AttributeError):
        return {"error": "Invalid date format."}

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

    return {
        "click_logs": click_logs,
        "total": total_clicks,
        "start": start,
        "limit": limit,
    }
