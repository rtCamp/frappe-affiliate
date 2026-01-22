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
        doc.commission_rate = apply_referral_fee_rules(doc)
        doc.calculate_commission()


def on_submit(doc, method=None):
    if doc.is_return:
        frappe.enqueue(void_referral_fee, doc=doc, timeout=3600)


def void_referral_fee(doc):
    returned_invoice = doc.return_against
    payment_entry_ref = frappe.get_all(
        "Payment Entry Reference",
        fields=["parent"],
        filters={
            "reference_doctype": "Sales Invoice",
            "reference_name": returned_invoice,
        },
    )
    for ref in payment_entry_ref:
        affiliate_fee = frappe.get_all(
            "Affiliate Referral",
            filters={"payment_entry": ref.parent, "tier": 0, "record_type": "referral"},
            fields=["name"],
        )
        for fee in affiliate_fee:
            frappe.set_value(
                "Affiliate Referral",
                fee.name,
                "void",
                1,
            )
