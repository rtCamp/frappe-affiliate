import frappe

from frappe_affiliate.api.commission_rule import get_commission_rule_for_tier


def on_submit(doc, method=None):
    payment_references = doc.get("references", [])
    sales_invoice = (
        payment_references[0].get("reference_name") if payment_references else None
    )
    sales_invoice_doc = (
        frappe.get_doc("Sales Invoice", sales_invoice) if sales_invoice else None
    )
    if not sales_invoice_doc:
        return
    if (
        sales_invoice_doc.sales_partner
        and sales_invoice_doc.total_commission
        and sales_invoice_doc.total_commission > 0
    ):
        record_referral(sales_invoice_doc, doc)


def record_referral(sales_invoice_doc, payment_entry_doc):
    referral = frappe.get_doc(
        {
            "doctype": "Affiliate Referral",
            "sales_partner": sales_invoice_doc.sales_partner,
            "payment_entry": payment_entry_doc.name,
            "amount": sales_invoice_doc.total_commission,
            "date": payment_entry_doc.posting_date,
            "record_type": "commission",
            "tier": 0,
        }
    ).save(ignore_permissions=True)

    record_referral_tiers(referral, sales_invoice_doc, payment_entry_doc.name)


def record_referral_tiers(referral, invoice, payment_entry):
    current_tier = 1
    sales_partner = referral.sales_partner

    while sales_partner and current_tier < 2:
        sales_partner_customer = frappe.db.get_value(
            "Sales Partner", sales_partner, "custom_customer"
        )
        parent_sales_partner = frappe.db.get_value(
            "Customer", sales_partner_customer, "default_sales_partner"
        )
        if not parent_sales_partner:
            return
        parent_banned = frappe.db.get_value(
            "Sales Partner", parent_sales_partner, "custom_banned"
        )
        sales_partner_user = frappe.db.get_value(
            "Sales Partner", parent_sales_partner, "custom_user"
        )
        if parent_banned:
            break

        affiliate_user_group = frappe.get_all(
            "User Group Member", filters={"user": sales_partner_user}, pluck="parent"
        )

        if "Affiliate Tier {}".format(current_tier) not in affiliate_user_group:
            sales_partner = parent_sales_partner
            current_tier += 1
            continue

        tier_commission_rate = get_commission_rule_for_tier(
            invoice, "Affiliate Tier {}".format(current_tier)
        )

        frappe.get_doc(
            {
                "doctype": "Affiliate Referral",
                "sales_partner": parent_sales_partner,
                "payment_entry": payment_entry,
                "amount": (referral.amount / 100) * tier_commission_rate,
                "date": referral.date,
                "record_type": "commission",
                "tier": current_tier,
            }
        ).save(ignore_permissions=True)

        current_tier += 1
        sales_partner = parent_sales_partner
