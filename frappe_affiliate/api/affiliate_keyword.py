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
        clicks = frappe.get_all(
            "Affiliate Click Log", filters=filters, fields=["remote_address"]
        )
        unique_clicks = frappe.get_all(
            "Affiliate Click Log",
            filters=filters,
            fields=["remote_address"],
            group_by="remote_address",
        )
        leads = frappe.get_all("Affiliate Lead Log", filters=filters, fields=["name"])
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
            "clicks": len(clicks),
            "uniqueClicks": len(unique_clicks),
            "leads": len(leads),
            "sales": len(sales),
            "referralFees": total_referral_fee,
        }

        keywords.append(keyword_dict)
    return keywords
