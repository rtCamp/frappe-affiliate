import frappe

from frappe_affiliate.api.sales_invoice import apply_referral_fee_rules


def validate(doc, method=None):
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


def on_submit(doc, method=None):
    is_return = doc.get("is_return", 0)
    if not is_return:
        return

    return_invoice = doc.get("return_against", None)
    if not return_invoice:
        return

    payment_entries = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": return_invoice},
        fields=["parent"],
        pluck="parent",
        group_by="parent",
    )

    referrals = frappe.get_all(
        "Affiliate Referral",
        filters={"payment_entry": ["in", payment_entries], "tier": 0},
        fields=["name"],
        pluck="name",
        distinct=True,
    )

    for referral in referrals:
        frappe.set_value("Affiliate Referral", referral, "void", 1)
