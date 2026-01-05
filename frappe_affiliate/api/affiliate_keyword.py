from functools import reduce
from operator import and_

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count, Sum
from frappe.utils import get_datetime


@frappe.whitelist(methods=["GET"])
def get_affiliate_keywords(
    start: int = 0,
    page_length: int = 20,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Get List of keywords with optional keyword and date filter with pagination.

    Args:
        start: Starting index for pagination (default: 0)
        page_length: Number of records per page (default: 20, max: 100)
        keyword: Filter by keyword (optional)
        date_from: Filter by start date (optional)
        date_to: Filter by end date (optional)

    Response:
    {
        "message": [
            {
                "keyword_name": string,
                "keyword": string,
                "clicks": number,
                "unique_clicks": number,
                "leads": number,
                "sales": number,
                "total_referral_fee": float
            }
        ],
        "total_count": number
    }
    """
    if date_from:
        date_from = get_datetime(date_from).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    if date_to:
        date_to = get_datetime(date_to).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )
    if not sales_partner:
        return []

    AffiliateKeyword = DocType("Affiliate Keyword")
    ClickLog = DocType("Affiliate Click Log")
    LeadLog = DocType("Affiliate Lead Log")
    Referral = DocType("Affiliate Referral")

    click_on_conditions = [
        ClickLog.keyword == AffiliateKeyword.name,
        ClickLog.sales_partner == sales_partner,
    ]
    if date_from:
        click_on_conditions.append(ClickLog.time >= date_from)
    if date_to:
        click_on_conditions.append(ClickLog.time <= date_to)

    lead_on_conditions = [
        LeadLog.keyword == AffiliateKeyword.name,
        LeadLog.sales_partner == sales_partner,
    ]
    if date_from:
        lead_on_conditions.append(LeadLog.time >= date_from)
    if date_to:
        lead_on_conditions.append(LeadLog.time <= date_to)

    referral_on_conditions = [
        Referral.keyword == AffiliateKeyword.name,
        Referral.sales_partner == sales_partner,
        Referral.record_type == "referral",
        Referral.void == 0,
    ]
    if date_from:
        referral_on_conditions.append(Referral.date >= date_from)
    if date_to:
        referral_on_conditions.append(Referral.date <= date_to)

    total_keywords = frappe.db.count(
        "Affiliate Keyword",
        filters={
            "sales_partner": sales_partner,
            "keyword": ("like", f"%{keyword}%") if keyword else ("!=", ""),
        },
    )

    q = (
        frappe.qb.from_(AffiliateKeyword)
        .left_join(ClickLog)
        .on(reduce(and_, click_on_conditions))
        .left_join(LeadLog)
        .on(reduce(and_, lead_on_conditions))
        .left_join(Referral)
        .on(reduce(and_, referral_on_conditions))
        .select(
            AffiliateKeyword.name.as_("keyword_name"),
            AffiliateKeyword.keyword,
            Count(ClickLog.name).as_("clicks"),
            Count(ClickLog.remote_address).distinct().as_("unique_clicks"),
            Count(LeadLog.name).as_("leads"),
            Count(Referral.name).as_("sales"),
            Sum(Referral.amount).as_("total_referral_fee"),
        )
        .where(AffiliateKeyword.sales_partner == sales_partner)
        .groupby(AffiliateKeyword.name)
        .orderby(AffiliateKeyword.keyword)
        .limit(page_length)
        .offset(start)
    )

    if keyword:
        q = q.where(AffiliateKeyword.keyword.like(f"%{keyword}%"))

    result = q.run(as_dict=True)

    # Format results: total_referral_fee can be None, replace with 0.0
    for r in result:
        if r["total_referral_fee"] is None:
            r["total_referral_fee"] = 0.0

    return {
        "message": result,
        "total": total_keywords,
    }
