import frappe
from frappe import _ as translate
from frappe.utils import getdate, nowdate


def update_coupon_code_count(coupon_code_doc, transaction_type):
    if coupon_code_doc:
        if transaction_type == "used":
            if not coupon_code_doc.custom_subscription_maximum_use:
                coupon_code_doc.custom_subscription_used_count = (
                    coupon_code_doc.custom_subscription_used_count + 1
                )
                coupon_code_doc.save(ignore_permissions=True)
            elif (
                coupon_code_doc.custom_subscription_used_count
                < coupon_code_doc.custom_subscription_maximum_use
            ):
                coupon_code_doc.custom_subscription_used_count = (
                    coupon_code_doc.custom_subscription_used_count + 1
                )
                coupon_code_doc.save(ignore_permissions=True)
            else:
                frappe.throw(translate("Allowed quantity is exhausted"))
        elif transaction_type == "cancelled":
            if coupon_code_doc.custom_subscription_used_count > 0:
                coupon_code_doc.custom_subscription_used_count = (
                    coupon_code_doc.custom_subscription_used_count - 1
                )
                coupon_code_doc.save(ignore_permissions=True)


def validate_coupon_code(
    coupon_code_doc, customer=None, is_new_subscription=False
) -> bool:
    if not coupon_code_doc:
        return False

    if isinstance(coupon_code_doc, str):
        coupon_doc_name = frappe.db.exists(
            "Coupon Code", {"coupon_code": coupon_code_doc}
        )
        if not coupon_doc_name:
            return False
        coupon_code_doc = frappe.get_doc("Coupon Code", coupon_doc_name)

    if is_new_subscription and coupon_code_doc.custom_disable:
        return False
    elif coupon_code_doc.valid_from and getdate(coupon_code_doc.valid_from) > getdate(
        nowdate()
    ):
        return False
    elif coupon_code_doc.valid_upto and getdate(coupon_code_doc.valid_upto) < getdate(
        nowdate()
    ):
        return False
    elif (
        coupon_code_doc.maximum_use
        and coupon_code_doc.used >= coupon_code_doc.maximum_use
    ):
        return False
    elif (
        coupon_code_doc.custom_subscription_maximum_use
        and coupon_code_doc.custom_subscription_used_count
        >= coupon_code_doc.custom_subscription_maximum_use
    ):
        return False

    if coupon_code_doc.customer and coupon_code_doc.customer != customer:
        return False

    if coupon_code_doc.custom_sales_partner:
        affiliate_banned = frappe.db.get_value(
            "Sales Partner",
            coupon_code_doc.custom_sales_partner,
            ["custom_banned", "custom_disabled"],
            as_dict=True,
        )
        if affiliate_banned.custom_disabled or affiliate_banned.custom_banned:
            return False

    return True
