import frappe


@frappe.whitelist()
def get_affiliate_cookie_timeout():
    return frappe.db.get_single_value("Affiliate Settings", "cookie_timeout") or 1


@frappe.whitelist()
def get_affiliate_settings():
    settings = frappe.get_single("Affiliate Settings")
    return {
        "cookie_timeout": settings.cookie_timeout or 1,
        "minimum_payout": settings.minimum_payout or 0,
        "delay_payout_days": settings.delay_payout_days or 0,
        "enable_keywords_support": settings.enable_keywords_support,
    }


@frappe.whitelist()
def get_banners_and_text_links():
    return_disabled = False
    if frappe.has_permission("Affiliate Settings", "write") is True:
        return_disabled = True
    user_groups = frappe.get_all(
        "User Group Member",
        filters={"user": frappe.session.user, "parenttype": "User Group"},
        pluck="parent",
    )
    fields = [
        "name",
        "type",
        "banner",
        "redirect_url",
        "title",
        "description",
        "width",
        "height",
        "disabled",
    ]
    if return_disabled:
        fields.append("available_for_user_group")
        fields.append("open_in_new_window")
    filters = {}
    if not return_disabled:
        filters["disabled"] = 0
        if user_groups:
            filters["available_for_user_group"] = ["in", [user_groups, "", None]]
        else:
            filters["available_for_user_group"] = ["in", ["", None]]
    banners_text_links = frappe.get_all(
        "Affiliate Banner and Text Link", filters=filters, fields=fields
    )
    for banner_text_link in banners_text_links:
        if banner_text_link.get("type") == "Banner" and banner_text_link.get("banner"):
            banner_text_link["banner"] = frappe.utils.get_url(
                frappe.db.get_value("File", banner_text_link.get("banner"), "file_url")
            )
    return banners_text_links
