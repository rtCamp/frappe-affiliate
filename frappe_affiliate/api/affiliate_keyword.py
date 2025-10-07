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
        clicks = frappe.db.count(
            "Affiliate Click Log", filters=filters, fields=["remote_address"]
        )
        unique_clicks = frappe.db.count(
            "Affiliate Click Log",
            filters=filters,
            fields=["remote_address"],
            group_by="remote_address",
        )
        leads = frappe.db.count("Affiliate Lead Log", filters=filters, fields=["name"])
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
            "uniqueClicks": unique_clicks,
            "leads": leads,
            "sales": len(sales),
            "commissions": total_referral_fee,
        }

        keywords.append(keyword_dict)
    return keywords
