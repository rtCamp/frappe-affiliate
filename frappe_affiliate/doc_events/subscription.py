import frappe
from frappe import _ as translate
from frappe_affiliate.utils.coupon_code import (
    update_coupon_code_count,
    validate_coupon_code,
)


def validate(doc, method=None):
    if frappe.flags.in_migrate:
        return

    if doc.custom_coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", doc.custom_coupon_code)
        coupon_code_valid = validate_coupon_code(coupon_code_doc)

        if not coupon_code_valid:
            frappe.throw(translate("Invalid coupon code"))

        if coupon_code_doc.customer:
            if coupon_code_doc.customer != doc.party:
                frappe.throw(translate("This coupon code is not valid for this user"))

        coupon_user_use_count = coupon_code_doc.get("custom_maximum_user_use_count", 0)
        if coupon_user_use_count > 0:
            user_use_count = frappe.db.count(
                "Subscription",
                {
                    "party_type": "Customer",
                    "party": doc.party,
                    "custom_coupon_code": doc.custom_coupon_code,
                },
            )
            if user_use_count >= coupon_user_use_count:
                frappe.throw(
                    translate(
                        "You have already used this coupon code for maximum allowed times."
                    )
                )
                return

        if doc.is_new():
            update_coupon_code_count(coupon_code_doc, "used")
