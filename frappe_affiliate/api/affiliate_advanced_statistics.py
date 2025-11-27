import frappe
from frappe.utils import (
    add_days,
    add_months,
    date_diff,
    formatdate,
    get_datetime,
    get_first_day,
    get_last_day,
    getdate,
)


@frappe.whitelist()
def get_affiliate_statistics_period():
    return [
        "Today",
        "Yesterday",
        "This Week (Sun - Sat)",
        "This Week (Mon - Sun)",
        "Last Week (Sun - Sat)",
        "Last Week (Mon - Sun)",
        "Last Business Week (Mon - Fri)",
        "This Month",
        "Last Month",
        "This Quarter",
        "Last Quarter",
        "This Year",
        "Last 7 Days",
        "Last 14 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Last 6 Months",
        "Last 12 Months",
        "Last Calendar Year",
        "All Time",
        "Exact",
    ]


def get_advanced_affiliate_statistics(
    user,
    period="All Time",
    grouping="Day",
    compare_previous_period=False,
    compare_same_period_last_year=False,
    start_date=None,
    end_date=None,
):
    """
    Get Statistics for Affiliates

    Args:
        user: User to get statistics for. Sales Partner is fetched based on this user.
        period: Time period for statistics (default: "All Time")
        grouping: Grouping of statistics (Day, Week, Month, Quarter, Year) (default: "Day")
        compare_previous_period (optional): Whether to compare with previous period (default: False)
        compare_same_period_last_year (optional): Whether to compare with same period last year (default: False)
        start_date (optional): Start date for the statistics (default: None)
        end_date (optional): End date for the statistics (default: None)

    Response:
    {
        "data": [
            {
                "period": "2025-10-20",
                "period_label": "October 20, 2025",
                "period_start": "2025-10-20",
                "period_end": "2025-10-20",
                "transactions": 5,
                "referral_fee_earned": 150.0,
                "clicks": 25,
                "unique_clicks": 20,
                // Only if compare_previous_period=True
                "transactions_previous_period": 3,
                "referral_fee_earned_previous_period": 90.0,
                "clicks_previous_period": 18,
                "unique_clicks_previous_period": 15,
                // Only if compare_same_period_last_year=True
                "transactions_previous_year": 2,
                "referral_fee_earned_previous_year": 60.0,
                "clicks_previous_year": 12,
                "unique_clicks_previous_year": 10
            }
        ],
        "period_info": {
            "period": "Today",
            "grouping": "Day",
            "start_date": "2025-10-20",
            "end_date": "2025-10-20",
            "compare_previous_period": true,
            "compare_same_period_last_year": true
        }
    }
    """
    if period not in get_affiliate_statistics_period():
        return {"error": "Invalid period. Please select a valid period."}
    if grouping not in ["Day", "Week", "Month", "Quarter", "Year"]:
        return {"error": "Invalid grouping. Please select a valid grouping."}

    affiliate_join = frappe.db.get_value(
        "Sales Partner", {"custom_user": user or frappe.session.user}, "creation"
    )

    if not affiliate_join:
        return {"error": "No affiliate record found for current user"}

    period_start, period_end = get_period_dates(
        period, start_date, end_date, affiliate_join
    )
    # Get main statistics
    main_data = get_grouped_statistics(period_start, period_end, grouping, user)

    # Get comparison data if requested
    prev_data = []
    ly_data = []

    if compare_previous_period:
        prev_start, prev_end = get_previous_period_dates(
            period_start, period_end, period
        )
        prev_data = get_grouped_statistics(prev_start, prev_end, grouping, user)

    if compare_same_period_last_year:
        ly_start, ly_end = get_same_period_last_year_dates(period_start, period_end)
        ly_data = get_grouped_statistics(ly_start, ly_end, grouping, user)

    # Merge comparison data into main data
    merged_data = merge_comparison_data(
        main_data,
        prev_data,
        ly_data,
        compare_previous_period,
        compare_same_period_last_year,
    )

    return {
        "data": merged_data,
        "period_info": {
            "period": period,
            "grouping": grouping,
            "start_date": formatdate(period_start, "yyyy-MM-dd"),
            "end_date": formatdate(period_end, "yyyy-MM-dd"),
            "compare_previous_period": compare_previous_period,
            "compare_same_period_last_year": compare_same_period_last_year,
        },
    }


def merge_comparison_data(main_data, prev_data, ly_data, compare_prev, compare_ly):
    """Merge comparison data as additional columns in the main data"""
    # Create lookup dictionaries for comparison data
    prev_lookup = {item["period"]: item for item in prev_data} if prev_data else {}
    ly_lookup = {item["period"]: item for item in ly_data} if ly_data else {}

    merged = []

    for main_item in main_data:
        merged_item = main_item.copy()

        # Add previous period columns if comparison is enabled
        if compare_prev:
            prev_item = prev_lookup.get(main_item["period"], {})
            merged_item.update(
                {
                    "transactions_previous_period": prev_item.get("transactions", 0),
                    "referral_fee_earned_previous_period": prev_item.get(
                        "referral_fee_earned", 0.0
                    ),
                    "clicks_previous_period": prev_item.get("clicks", 0),
                    "unique_clicks_previous_period": prev_item.get("unique_clicks", 0),
                }
            )

        # Add last year columns if comparison is enabled
        if compare_ly:
            ly_item = ly_lookup.get(main_item["period"], {})
            merged_item.update(
                {
                    "transactions_previous_year": ly_item.get("transactions", 0),
                    "referral_fee_earned_previous_year": ly_item.get(
                        "referral_fee_earned", 0.0
                    ),
                    "clicks_previous_year": ly_item.get("clicks", 0),
                    "unique_clicks_previous_year": ly_item.get("unique_clicks", 0),
                }
            )

        merged.append(merged_item)

    return merged


def get_previous_period_dates(start_date, end_date, period):
    """Get the previous period dates based on the current period"""
    period_length = date_diff(end_date, start_date) + 1

    if period in ["Today", "Yesterday"]:
        # Previous day
        prev_end = add_days(start_date, -1)
        prev_start = prev_end
    elif "Week" in period:
        # Previous week
        prev_end = add_days(start_date, -1)
        prev_start = add_days(prev_end, -6)
    elif period in ["This Month", "Last Month"]:
        # Previous month
        prev_end = add_days(start_date, -1)
        prev_start = get_first_day(prev_end)
    elif "Quarter" in period:
        # Previous quarter
        prev_end = add_days(start_date, -1)
        prev_start = add_months(start_date, -3)
    elif "Year" in period:
        # Previous year
        prev_start = start_date.replace(year=start_date.year - 1)
        prev_end = end_date.replace(year=end_date.year - 1)
    else:
        # For other periods (Last X Days, etc.), go back by the same duration
        prev_end = add_days(start_date, -1)
        prev_start = add_days(prev_end, -(period_length - 1))

    return prev_start, prev_end


def get_same_period_last_year_dates(start_date, end_date):
    """Get the same period dates from last year"""
    try:
        ly_start = start_date.replace(year=start_date.year - 1)
        ly_end = end_date.replace(year=end_date.year - 1)
    except ValueError:
        # Handle leap year edge case (Feb 29)
        if start_date.month == 2 and start_date.day == 29:
            ly_start = start_date.replace(year=start_date.year - 1, day=28)
        else:
            ly_start = start_date.replace(year=start_date.year - 1)

        if end_date.month == 2 and end_date.day == 29:
            ly_end = end_date.replace(year=end_date.year - 1, day=28)
        else:
            ly_end = end_date.replace(year=end_date.year - 1)

    return ly_start, ly_end


def get_period_dates(period, start_date=None, end_date=None, affiliate_join=None):
    """Get start and end dates based on the selected period"""
    today = getdate()

    if period == "Exact" and start_date and end_date:
        return getdate(start_date), getdate(end_date)

    if period == "Today":
        return today, today
    elif period == "Yesterday":
        yesterday = add_days(today, -1)
        return yesterday, yesterday
    elif period == "This Week (Sun - Sat)":
        # Find last Sunday
        days_since_sunday = today.weekday() + 1 if today.weekday() != 6 else 0
        week_start = add_days(today, -days_since_sunday)
        week_end = add_days(week_start, 6)
        return week_start, week_end
    elif period == "This Week (Mon - Sun)":
        # Find last Monday
        days_since_monday = today.weekday()
        week_start = add_days(today, -days_since_monday)
        week_end = add_days(week_start, 6)
        return week_start, week_end
    elif period == "Last Week (Sun - Sat)":
        days_since_sunday = today.weekday() + 1 if today.weekday() != 6 else 0
        this_week_start = add_days(today, -days_since_sunday)
        last_week_start = add_days(this_week_start, -7)
        last_week_end = add_days(last_week_start, 6)
        return last_week_start, last_week_end
    elif period == "Last Week (Mon - Sun)":
        days_since_monday = today.weekday()
        this_week_start = add_days(today, -days_since_monday)
        last_week_start = add_days(this_week_start, -7)
        last_week_end = add_days(last_week_start, 6)
        return last_week_start, last_week_end
    elif period == "Last Business Week (Mon - Fri)":
        days_since_monday = today.weekday()
        this_week_start = add_days(today, -days_since_monday)
        last_week_start = add_days(this_week_start, -7)
        last_week_end = add_days(last_week_start, 4)  # Friday
        return last_week_start, last_week_end
    elif period == "This Month":
        return get_first_day(today), get_last_day(today)
    elif period == "Last Month":
        last_month = add_months(today, -1)
        return get_first_day(last_month), get_last_day(last_month)
    elif period == "This Quarter":
        quarter_start = get_first_day(today)
        quarter_start = quarter_start.replace(month=((today.month - 1) // 3) * 3 + 1)
        quarter_end = add_months(quarter_start, 3)
        quarter_end = add_days(quarter_end, -1)
        return quarter_start, quarter_end
    elif period == "Last Quarter":
        this_quarter_start = get_first_day(today)
        this_quarter_start = this_quarter_start.replace(
            month=((today.month - 1) // 3) * 3 + 1
        )
        last_quarter_start = add_months(this_quarter_start, -3)
        last_quarter_end = add_days(this_quarter_start, -1)
        return last_quarter_start, last_quarter_end
    elif period == "This Year":
        return getdate(f"{today.year}-01-01"), getdate(f"{today.year}-12-31")
    elif period == "Last 7 Days":
        return add_days(today, -6), today
    elif period == "Last 14 Days":
        return add_days(today, -13), today
    elif period == "Last 30 Days":
        return add_days(today, -29), today
    elif period == "Last 90 Days":
        return add_days(today, -89), today
    elif period == "Last 6 Months":
        return add_months(today, -6), today
    elif period == "Last 12 Months":
        return add_months(today, -12), today
    elif period == "Last Calendar Year":
        last_year = today.year - 1
        return getdate(f"{last_year}-01-01"), getdate(f"{last_year}-12-31")
    elif period == "All Time":
        return affiliate_join.date() if affiliate_join else getdate("2000-01-01"), today

    return today, today


def get_grouped_statistics(start_date, end_date, grouping, user=None):
    """Get statistics grouped by the specified grouping (Day, Week, Month, Quarter, Year)"""
    data = []
    current_date = start_date

    while current_date <= end_date:
        if grouping == "Day":
            period_start = current_date
            period_end = current_date
            next_date = add_days(current_date, 1)
            period_label = formatdate(current_date, "MMMM dd, yyyy")
            period_key = formatdate(current_date, "yyyy-MM-dd")
        elif grouping == "Week":
            # Start from Monday of the week
            days_since_monday = current_date.weekday()
            period_start = add_days(current_date, -days_since_monday)
            period_end = add_days(period_start, 6)
            period_end = min(period_end, end_date)
            next_date = add_days(period_start, 7)
            period_label = f"Week of {formatdate(period_start, 'MMMM dd, yyyy')}"
            period_key = f"{formatdate(period_start, 'yyyy-MM-dd')}_week"
        elif grouping == "Month":
            period_start = get_first_day(current_date)
            period_end = get_last_day(current_date)
            period_end = min(period_end, end_date)
            next_date = add_months(current_date, 1)
            period_label = formatdate(current_date, "MMMM yyyy")
            period_key = formatdate(current_date, "yyyy-MM")
        elif grouping == "Quarter":
            quarter_month = ((current_date.month - 1) // 3) * 3 + 1
            period_start = current_date.replace(month=quarter_month, day=1)
            period_end = add_months(period_start, 3)
            period_end = add_days(period_end, -1)
            period_end = min(period_end, end_date)
            next_date = add_months(period_start, 3)
            period_label = f"Q{(quarter_month - 1) // 3 + 1} {current_date.year}"
            period_key = f"{current_date.year}-Q{(quarter_month - 1) // 3 + 1}"
        elif grouping == "Year":
            period_start = current_date.replace(month=1, day=1)
            period_end = current_date.replace(month=12, day=31)
            period_end = min(period_end, end_date)
            next_date = current_date.replace(year=current_date.year + 1)
            period_label = str(current_date.year)
            period_key = str(current_date.year)

        if period_start > end_date:
            break

        stats = get_period_statistics(period_start, period_end, user)
        stats["period"] = period_key
        stats["period_label"] = period_label
        stats["period_start"] = formatdate(period_start, "yyyy-MM-dd")
        stats["period_end"] = formatdate(period_end, "yyyy-MM-dd")

        data.append(stats)
        current_date = next_date

    return data


def get_period_statistics(start_date, end_date, user=None):
    """Get affiliate statistics for a specific period"""
    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": user or frappe.session.user}, "name"
    )

    if not sales_partner:
        return {
            "transactions": 0,
            "referral_fee_earned": 0.0,
            "clicks": 0,
            "unique_clicks": 0,
        }

    start_datetime = get_datetime(start_date)
    end_datetime = get_datetime(end_date).replace(hour=23, minute=59, second=59)

    sales = frappe.get_all(
        "Affiliate Referral",
        filters={
            "sales_partner": sales_partner,
            "record_type": "commission",
            "date": ["between", [start_datetime, end_datetime]],
            "void": 0,
        },
        fields="amount",
        pluck="amount",
    )
    void_sales = frappe.get_all(
        "Affiliate Referral",
        filters={
            "sales_partner": sales_partner,
            "record_type": "void",
            "date": ["between", [start_datetime, end_datetime]],
            "void": 0,
        },
        fields="amount",
        pluck="amount",
    )
    sales_count = len(sales)
    total_referral_fee = sum(sales) - sum(void_sales)

    clicks_count = frappe.db.count(
        "Affiliate Click Log",
        filters={
            "sales_partner": sales_partner,
            "time": ["between", [start_datetime, end_datetime]],
        },
    )
    unique_clicks_count = frappe.get_all(
        "Affiliate Click Log",
        filters={
            "sales_partner": sales_partner,
            "time": ["between", [start_datetime, end_datetime]],
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
