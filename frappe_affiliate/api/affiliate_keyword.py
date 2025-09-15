import frappe


@frappe.whitelist()
def get_affiliate_keywords():
    keywords = frappe.db.get_all(
        "Affiliate Keyword",
        filters={"sales_partner": frappe.session.user},
        fields=["keyword"],
        pluck="keyword",
    )
    return keywords
