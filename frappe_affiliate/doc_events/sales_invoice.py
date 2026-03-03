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

    original_invoice_value = frappe.get_value("Sales Invoice", return_invoice, "total")
    return_invoice_value = doc.total

    if return_invoice_value > 0:
        return

    percentage_deduction = abs(return_invoice_value) / original_invoice_value

    payment_entries = frappe.get_list(
        "Payment Entry Reference",
        filters={"reference_name": return_invoice},
        fields=["parent"],
        pluck="parent",
        group_by="parent",
    )

    referrals = frappe.get_list(
        "Affiliate Referral",
        filters={
            "payment_entry": ["in", payment_entries],
            "void": 0,
            "record_type": "referral",
        },
        fields=["name"],
        pluck="name",
        distinct=True,
    )

    for referral in referrals:
        frappe.db.set_value(
            "Affiliate Referral", referral, "void", 1
        )  # Set through frappe.db to avoid triggering events
        voided_referral = frappe.get_doc("Affiliate Referral", referral)
        void_referral_doc = frappe.new_doc("Affiliate Referral")

        adjusted_amount = voided_referral.amount * percentage_deduction

        set_values = {
            "sales_partner": voided_referral.sales_partner,
            "payment_entry": voided_referral.payment_entry,
            "amount": adjusted_amount,
            "record_type": "void",
            "tier": 0,
            "void": 0,
            "void_affiliate_referral": voided_referral.name,
            "date": frappe.utils.nowdate(),
        }

        void_referral_doc.update(set_values)
        void_referral_doc.deferred_insert()
