import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import cint, getdate, nowdate


@frappe.whitelist(methods=["GET"])
def get_affiliate_coupons(start: str | int = 0, limit: str | int = 20):
    start = max(0, cint(start))
    limit = max(cint(limit), 0)

    result = {"coupon_codes": [], "total": 0, "start": start, "limit": limit}

    user = frappe.session.user
    if user == "Guest":
        return result

    sales_partner = frappe.db.get_value(
        "Sales Partner", {"custom_user": user}, "name", cache=True
    )
    if not sales_partner:
        return result

    partner_status = frappe.db.get_value(
        "Sales Partner",
        sales_partner,
        ["custom_banned", "custom_disabled"],
        as_dict=True,
    )
    if partner_status.custom_banned or partner_status.custom_disabled:
        return result

    today = nowdate()
    CC = DocType("Coupon Code")

    base = (
        frappe.qb.from_(CC)
        .where(CC.custom_sales_partner == sales_partner)
        .where(CC.custom_disable == 0)
        .where((CC.valid_upto.isnull()) | (CC.valid_upto >= today))
        .where((CC.valid_from.isnull()) | (CC.valid_from <= today))
        .where(
            (CC.maximum_use.isnull())
            | (CC.maximum_use == 0)
            | (CC.used < CC.maximum_use)
        )
        .where(
            (CC.custom_subscription_maximum_use.isnull())
            | (CC.custom_subscription_maximum_use == 0)
            | (CC.custom_subscription_used_count < CC.custom_subscription_maximum_use)
        )
    )

    result["coupon_codes"] = [
        row[0] for row in base.select(CC.coupon_code).offset(start).limit(limit).run()
    ]
    result["total"] = base.select(Count("*")).run()[0][0]

    return result


@frappe.whitelist()
def validate_coupon_code(coupon_code: str, customer: str | None = None):
    if not coupon_code:
        return {"valid": False, "message": "No coupon code provided"}

    coupon = frappe.get_doc("Coupon Code", coupon_code)

    if coupon.custom_disable:
        return {"valid": False, "message": "This coupon code is not valid anymore"}

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

    if customer and coupon.customer:
        if coupon.customer != customer:
            return {
                "valid": False,
                "message": "This coupon code is not valid for this user",
            }
    elif customer is None and coupon.customer:
        return {
            "valid": False,
            "message": "This coupon code is not valid for this user",
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
