import frappe


@frappe.whitelist()
def get_affiliate_keywords():
    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )
    if not sales_partner:
        return []
    keywords_list = frappe.get_all(
        "Affiliate Keyword",
        filters={"sales_partner": sales_partner},
        fields=["name", "keyword"],
    )

    keywords = []

    for keyword in keywords_list:
        filters = {"sales_partner": sales_partner, "keyword": keyword.name}
        clicks = frappe.db.count("Affiliate Click Log", filters=filters)
        unique_clicks = frappe.get_all(
            "Affiliate Click Log",
            filters=filters,
            group_by="remote_address",
            fields=["name"],
        )
        leads = frappe.db.count("Affiliate Lead Log", filters=filters)
        sales = frappe.get_all(
            "Affiliate Referral",
            filters={
                "sales_partner": sales_partner,
                "keyword": keyword.name,
                "record_type": "commission",
                "void": 0,
            },
            fields="amount",
        )
        total_referral_fee = sum(sales)
        keyword_dict = {
            "keyword": keyword.keyword,
            "clicks": clicks,
            "uniqueClicks": len(unique_clicks),
            "leads": leads,
            "sales": len(sales),
            "total_referral_fee": total_referral_fee,
        }

        keywords.append(keyword_dict)
    return keywords
