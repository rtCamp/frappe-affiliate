import frappe
from frappe import _ as translate

from frappe_affiliate.utils.coupon_code import (
    validate_coupon_code,
)


def validate(doc, method=None):
    if frappe.flags.in_migrate:
        return

    if doc.custom_coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", doc.custom_coupon_code)
        coupon_code_valid = validate_coupon_code(
            coupon_code_doc, doc.party, doc.is_new()
        )

        if not coupon_code_valid:
            frappe.throw(translate("Invalid coupon code"))

        if coupon_code_doc.custom_sales_partner:
            sales_partner_customer = frappe.db.get_value(
                "Sales Partner", coupon_code_doc.custom_sales_partner, "custom_customer"
            )
            if doc.party == sales_partner_customer:
                frappe.throw(
                    translate(
                        "Cannot use coupon code assigned to your own affiliate account."
                    )
                )

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


def before_insert(doc, method=None):
    if frappe.flags.in_migrate:
        return

    linked_affiliate = None

    if doc.party_type != "Customer":
        return

    if doc.custom_coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", doc.custom_coupon_code)
        if coupon_code_doc.customer and coupon_code_doc.customer != doc.party:
            frappe.throw(translate("This coupon code is not valid for this user"))
        if coupon_code_doc.custom_sales_partner:
            linked_affiliate = coupon_code_doc.custom_sales_partner
    else:
        customer_affiliate = frappe.db.get_value(
            "Customer", doc.party, "default_sales_partner"
        )
        if customer_affiliate and customer_affiliate != "":
            linked_affiliate = customer_affiliate

    if linked_affiliate:
        affiliate_banned = frappe.db.get_value(
            "Sales Partner",
            linked_affiliate,
            ["custom_banned", "custom_disabled"],
            as_dict=True,
        )
        if not affiliate_banned.custom_disabled and not affiliate_banned.custom_banned:
            doc.custom_affiliate = linked_affiliate
