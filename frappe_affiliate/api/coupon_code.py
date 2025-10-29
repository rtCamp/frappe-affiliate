import frappe
from frappe.utils import getdate, nowdate


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

    if coupon.valid_from and getdate(coupon.valid_from) > getdate(nowdate()):
        return {
            "valid": False,
            "message": "This coupon code's validity has not started",
        }

    if coupon.valid_upto and getdate(coupon.valid_upto) < getdate(nowdate()):
        return {"valid": False, "message": "This coupon code has expired"}

    if coupon.maximum_use and coupon.used >= coupon.maximum_use:
        return {
            "valid": False,
            "message": "This coupon code has reached its maximum usage limit",
        }

    if (
        coupon.custom_subscription_maximum_use
        and coupon.custom_subscription_used_count
        >= coupon.custom_subscription_maximum_use
    ):
        return {
            "valid": False,
            "message": "This coupon code has reached its maximum usage limit",
        }

    affiliate = False
    if coupon.custom_sales_partner:
        affiliate_banned = frappe.db.get_value(
            "Sales Partner",
            coupon.custom_sales_partner,
            ["custom_banned", "custom_disabled"],
            as_dict=True,
        )
        if affiliate_banned.custom_disabled or affiliate_banned.custom_banned:
            return {"valid": False, "message": "This coupon code is no longer valid"}

        affiliate = True

    return {
        "valid": True,
        "message": "This coupon code is valid",
        "affiliate": affiliate,
    }
