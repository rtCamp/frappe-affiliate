import frappe


@frappe.whitelist()
def get_affiliate_keywords():
    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": frappe.session.user}, "name"
    )
    if not sales_partner:
        return []
    keywords = frappe.get_all(
        "Affiliate Keyword",
        filters={"sales_partner": sales_partner},
        fields=["keyword"],
    )
    return keywords
