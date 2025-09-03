import frappe

@frappe.whitelist()
def get_banners():
    banners = frappe.get_single("Affiliate Settings").banners
    return banners

@frappe.whitelist()
def get_affiliate_coupons(affiliate_id):
    coupon_codes = frappe.db.get_list(
        "Coupon Code",
        {"custom_sales_partner": affiliate_id},
        fields=["coupon_code"],
        pluck="coupon_code",
    )
    return coupon_codes
