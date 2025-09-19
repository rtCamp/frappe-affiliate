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
def get_banners():
    banners = frappe.get_single("Affiliate Settings").banners
    banners_list = []
    for banner in banners:
        banner_dict = {
            "name": banner.name,
            "image": frappe.utils.get_url(
                frappe.db.get_value("File", banner.banner, "file_url")
            ),
            "url": banner.url,
            "title": banner.title,
            "description": banner.description,
            "width": banner.width,
            "height": banner.height,
            "disabled": banner.disabled,
        }
        banners_list.append(banner_dict)
    return banners_list
