import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from frappe.utils import cint, nowdate


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
