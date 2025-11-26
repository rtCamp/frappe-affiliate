import frappe


def record_lead(data, user):
    affiliate = data.get("affiliate")
    if not affiliate:
        return
    lead_log = frappe.new_doc("Affiliate Lead Log")

    lead_log.sales_partner = affiliate
    lead_log.time = frappe.utils.now_datetime()
    lead_log.remote_address = data.get("remote_address", None)
    if data.get("banner_text_link", None):
        lead_log.banner_id = data["banner_text_link"]
    enable_keywords_support = frappe.get_cached_doc(
        "Affiliate Settings"
    ).enable_keywords_support
    if enable_keywords_support:
        lead_log.keyword = data.get("keyword", None)
    lead_log.referrer = data.get("referrer", None)
    lead_log.first_visited = data.get("first_visited", None)
    lead_log.user = user
    lead_log.save(ignore_permissions=True)
