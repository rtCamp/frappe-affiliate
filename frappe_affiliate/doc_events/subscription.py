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
