import frappe
from frappe.utils import escape_html


def record_click(username, banner=None):
    click_log = frappe.new_doc("Affiliate Click Log")
    user = frappe.db.get_value("User", {"username": username, "enabled": 1}, "name")
    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": user, "custom_banned": 0}, "name"
    )
    if not sales_partner:
        return
    click_log.sales_partner = sales_partner
    click_log.time = frappe.utils.now_datetime()
    click_log.user_agent = frappe.local.request.headers.get("User-Agent")
    click_log.remote_address = frappe.local.request.remote_addr
    if banner:
        click_log.banner_id = banner
    keyword = frappe.local.request.args.get("keyword", None)
    keyword_name = None
    if keyword and keyword != "":
        keyword = escape_html(keyword)
        keyword_exists = frappe.db.exists(
            "Affiliate Keyword", {"keyword": keyword, "sales_partner": sales_partner}
        )
        if not keyword_exists:
            keyword_doc = frappe.new_doc("Affiliate Keyword")
            keyword_doc.keyword = keyword
            keyword_doc.sales_partner = sales_partner
            keyword_doc.save(ignore_permissions=True)
            keyword_name = keyword_doc.name
        else:
            keyword_name = frappe.db.get_value(
                "Affiliate Keyword",
                {"keyword": keyword, "sales_partner": sales_partner},
                "name",
            )
    click_log.keyword = keyword_name
    click_log.referrer = frappe.local.request.referrer
    click_log.save(ignore_permissions=True)
    frappe.db.commit()  # nosemgrep Manual commit as after this exception is raised, which will reverse it if not committed.
    return click_log.name
