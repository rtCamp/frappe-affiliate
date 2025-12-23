import frappe
from frappe import _ as translate

from frappe_affiliate.api.sales_invoice import apply_referral_fee_rules


def validate(doc, method=None):
    coupon_code = doc.get("coupon_code", None)
    if coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", coupon_code)
        if coupon_code_doc.customer:
            if coupon_code_doc.customer != doc.customer:
                frappe.throw(translate("This coupon code is not valid for this user"))
        if (
            coupon_code_doc.custom_sales_partner
            and coupon_code_doc.custom_sales_partner != doc.sales_partner
        ):
            affiliate_banned = frappe.db.get_value(
                "Sales Partner",
                coupon_code_doc.custom_sales_partner,
                ["custom_banned", "custom_disabled"],
                as_dict=True,
            )
            if (
                not affiliate_banned.custom_disabled
                and not affiliate_banned.custom_banned
            ):
                doc.sales_partner = coupon_code_doc.custom_sales_partner

    if doc.sales_partner:
        affiliate_banned = frappe.db.get_value(
            "Sales Partner",
            doc.sales_partner,
            ["custom_banned", "custom_disabled"],
            as_dict=True,
        )
        if affiliate_banned.custom_disabled == 1 or affiliate_banned.custom_banned == 1:
            doc.sales_partner = None
            doc.commission_rate = None
            return
        referral_fee_rate = apply_referral_fee_rules(doc)
        # In case there is no applicable referral fee rule, reset sales partner
        if not referral_fee_rate:
            doc.sales_partner = None
        doc.commission_rate = referral_fee_rate
        doc.calculate_commission()
