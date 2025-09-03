import frappe

@frappe.whitelist()
def get_banners():
    banners = frappe.get_single("Affiliate Settings").banners
    banners_list = []
    for banner in banners:
        banner_dict = {
            "name": banner.name,
            "image": frappe.utils.get_url(frappe.db.get_value("File", banner.banner_link, "file_url")),
            "url": banner.url,
            "title": banner.title,
            "description": banner.description,
            "width":banner.width,
            "height":banner.height
        }
        banners_list.append(banner_dict)
    return banners_list

@frappe.whitelist()
def get_affiliate_coupons(affiliate_id):
    coupon_codes = frappe.db.get_list(
        "Coupon Code",
        filters={"custom_sales_partner": affiliate_id},
        fields=["coupon_code"],
        pluck="coupon_code",
    )
    return coupon_codes
