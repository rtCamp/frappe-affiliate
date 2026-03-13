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
    if not doc.get("is_return"):
        return

    return_invoice = doc.get("return_against")
    if not return_invoice:
        return

    original_invoice_value = frappe.db.get_value(
        "Sales Invoice", return_invoice, "total"
    )
    return_invoice_value = doc.total

    if not original_invoice_value or return_invoice_value >= 0:
        return

    percentage_deduction = abs(return_invoice_value) / original_invoice_value

    payment_entries = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": return_invoice},
        pluck="parent",
        distinct=True,
    )

    if not payment_entries:
        return

    referrals = frappe.get_all(
        "Affiliate Referral",
        filters={
            "payment_entry": ["in", payment_entries],
            "void": 0,
            "record_type": "referral",
        },
        fields=["name", "amount", "sales_partner", "payment_entry"],
    )

    if not referrals:
        return

    referral_names = [ref.name for ref in referrals]

    frappe.db.set_value(
        "Affiliate Referral", {"name": ["in", referral_names]}, "void", 1
    )

    current_date = frappe.utils.nowdate()

    for ref in referrals:
        adjusted_amount = ref.amount * percentage_deduction

        void_referral_doc = frappe.new_doc("Affiliate Referral")

        void_referral_doc.update(
            {
                "sales_partner": ref.sales_partner,
                "payment_entry": ref.payment_entry,
                "amount": adjusted_amount,
                "record_type": "void",
                "tier": 0,
                "void": 0,
                "void_affiliate_referral": ref.name,
                "date": current_date,
            }
        )

        void_referral_doc.deferred_insert()
