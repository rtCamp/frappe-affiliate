import frappe


@frappe.whitelist()
def get_affiliate_coupons(affiliate_id):
    user = frappe.db.get_value("User", {"username": affiliate_id}, "name")
    sales_partner = frappe.db.get_value("Sales Partner", {"custom_user": user}, "name")
    coupon_codes = frappe.db.get_list(
        "Coupon Code",
        filters={"custom_sales_partner": sales_partner},
        fields=["coupon_code"],
        pluck="coupon_code",
        ignore_permissions=True,
    )
    return coupon_codes


@frappe.whitelist()
def validate_coupon_code(coupon_code):
    if not coupon_code:
        return {"valid": False, "message": "No coupon code provided"}

    coupon = frappe.get_doc("Coupon Code", coupon_code)
    if coupon.disabled:
        return {"valid": False, "message": "This coupon code is no longer valid"}

    if coupon.valid_upto and coupon.valid_upto < frappe.utils.nowdate():
        return {"valid": False, "message": "This coupon code has expired"}

    affiliate = False
    if coupon.custom_sales_partner:
        sales_partner = frappe.db.get_value(
            "Sales Partner", {"name": coupon.custom_sales_partner}, "name"
        )
        if sales_partner:
            affiliate = True

    return {
        "valid": True,
        "message": "This coupon code is valid",
        "affiliate": affiliate,
    }
