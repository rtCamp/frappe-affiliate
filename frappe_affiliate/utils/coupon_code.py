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
    coupon_code_doc, customer=None, is_new_subscription=False, item=None
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

    if item:
        pricing_rule = coupon_code_doc.get("pricing_rule")
        if pricing_rule:
            if not check_item_in_coupon_pricing_rule([item], pricing_rule):
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


def check_item_in_coupon_pricing_rule(item_list, pricing_rule):
    apply_on_specific = frappe.get_all(
        "Pricing Rule Item Code",
        filters={
            "parent": pricing_rule,
            "parenttype": "Pricing Rule",
            "parentfield": "items",
        },
    )
    if apply_on_specific and apply_on_specific != []:
        apply_on = frappe.get_all(
            "Pricing Rule Item Code",
            filters={
                "parent": pricing_rule,
                "parenttype": "Pricing Rule",
                "item_code": ["in", item_list],
                "parentfield": "items",
            },
        )
        if not apply_on:
            return False
    apply_except = frappe.get_all(
        "Pricing Rule Item Code",
        filters={
            "parent": pricing_rule,
            "parenttype": "Pricing Rule",
            "item_code": ["in", item_list],
            "parentfield": "custom_apply_except_item_code",
        },
    )
    if apply_except and apply_except != []:
        return False
    return True

def get_first_recurring_discount(coupon_code, recurring=False):
    result = {
        "type": None,
        "value": 0.0,
    }

    if not coupon_code:
        return result

    coupon_code_doc = frappe.get_doc("Coupon Code", coupon_code, cache=True)
    if not coupon_code_doc:
        return result
    apply_to_recurring = coupon_code_doc.get("custom_apply_to_recurring")
    if recurring and not apply_to_recurring:
        return result
    pricing_rule_field = (
        "custom_recurring_pricing_rule" if recurring else "pricing_rule"
    )

    pricing_rule = coupon_code_doc.get(pricing_rule_field)
    if not pricing_rule:
        return result
    pricing_rule_doc = frappe.get_doc("Pricing Rule", pricing_rule, cache=True)
    if not pricing_rule_doc:
        return result
    field_name = (
        "discount_percentage"
        if pricing_rule_doc.rate_or_discount == "Discount Percentage"
        else "discount_amount"
    )
    result["type"] = field_name
    result["value"] = pricing_rule_doc.get(field_name) or 0.0
    return result
