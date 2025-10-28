import frappe
from frappe import _ as translate


def validate(doc, method=None):
    if doc.custom_coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", doc.custom_coupon_code)
        coupon_user_use_count = coupon_code_doc.get("custom_maximum_user_use_count", 0)
        if coupon_user_use_count > 0:
            user_use_count = frappe.db.count(
                "Subscription",
                {
                    "party_type": "Customer",
                    "party": doc.party,
                    "coupon_code": doc.custom_coupon_code,
                },
            )
            if user_use_count >= coupon_user_use_count:
                frappe.throw(
                    translate(
                        "You have already used this coupon code for maximum allowed times."
                    )
                )
                return
        if coupon_code_doc.custom_sales_partner:
            affiliate_banned = frappe.db.get_value(
                "Sales Partner",
                coupon_code_doc.custom_sales_partner,
                ["custom_banned", "custom_disabled"],
                as_dict=True,
            )
            if affiliate_banned.custom_disabled or affiliate_banned.custom_banned:
                frappe.throw(translate("Coupon code is no longer valid."))
