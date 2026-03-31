import frappe

from frappe_affiliate.api.referral_fee_rule import get_referral_fee_rule_for_tier
from frappe_affiliate.utils.coupon_code import (
    update_coupon_code_count,
)


def on_submit(doc, method=None):
    if frappe.flags.in_migrate:
        return
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

    if not sales_invoice_doc.custom_apex_public_id:
        return
    sales_invoice_count = sales_invoice_doc.custom_apex_public_id.split("/")[-1]
    if sales_invoice_count == "1" and sales_invoice_doc.coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", sales_invoice_doc.coupon_code)
        update_coupon_code_count(coupon_code_doc, "used")


def record_referral(sales_invoice_doc, payment_entry_doc):
    keyword = get_keyword_for_referral()
    referral = frappe.get_doc(
        {
            "doctype": "Affiliate Referral",
            "sales_partner": sales_invoice_doc.sales_partner,
            "payment_entry": payment_entry_doc.name,
            "amount": sales_invoice_doc.total_commission,
            "date": payment_entry_doc.posting_date,
            "record_type": "referral",
            "tier": 0,
        }
    )

    if keyword:
        referral.keyword = keyword

    referral.save()

    if frappe.get_single_value("Affiliate Settings", "enable_tier_2"):
        referral_2 = record_referral_tiers(
            referral, sales_invoice_doc, payment_entry_doc.name, 2
        )
        if (
            frappe.get_single_value("Affiliate Settings", "enable_tier_3")
            and referral_2
        ):
            record_referral_tiers(
                referral_2, sales_invoice_doc, payment_entry_doc.name, 3
            )


def record_referral_tiers(referral, invoice, payment_entry, tier):
    sales_partner = referral.sales_partner

    sales_partner_customer = frappe.db.get_value(
        "Sales Partner", sales_partner, "custom_customer"
    )
    parent_sales_partner = frappe.db.get_value(
        "Customer", sales_partner_customer, "default_sales_partner"
    )
    if not parent_sales_partner:
        return
    parent_banned = frappe.db.get_value(
        "Sales Partner",
        parent_sales_partner,
        ["custom_banned", "custom_disabled"],
        as_dict=True,
    )
    sales_partner_user = frappe.db.get_value(
        "Sales Partner", parent_sales_partner, "custom_user"
    )
    if parent_banned.custom_disabled == 1 or parent_banned.custom_banned == 1:
        return

    affiliate_user_group = frappe.get_all(
        "User Group Member", filters={"user": sales_partner_user}, pluck="parent"
    )

    # ToDo: investigate if get_list can be used here instead of get_all. If so then replace it.
    tier_user_groups = frappe.get_all(
        "Referral User Group",
        filters={"parentfield": f"tier_{tier}_groups", "parent": "Affiliate Settings"},
        fields=["user_group"],
        pluck="user_group",
    )

    if tier_user_groups and set(affiliate_user_group).isdisjoint(tier_user_groups):
        return

    tier_referral_fee_rate = get_referral_fee_rule_for_tier(invoice, tier_user_groups)

    if not tier_referral_fee_rate or tier_referral_fee_rate <= 0:
        frappe.log_error(
            message=f"No valid referral fee rate found for tier {tier} for payment entry {payment_entry}",
            title="Referral Fee Rate Not Found",
        )
        return

    new_referral = frappe.get_doc(
        {
            "doctype": "Affiliate Referral",
            "sales_partner": parent_sales_partner,
            "payment_entry": payment_entry,
            "amount": (referral.amount / 100) * tier_referral_fee_rate,
            "date": referral.date,
            "record_type": "referral",
            "tier": tier - 1,
        }
    ).save()

    return new_referral


def get_keyword_for_referral():
    request = getattr(frappe.local, "request", None)
    if not request or not hasattr(request, "cookies"):
        return

    aff_cookie = request.cookies.get("affiliate_id")
    if not aff_cookie:
        return

    aff_cookie_parts = aff_cookie.split("-")
    if len(aff_cookie_parts) < 2:
        return

    click_log = frappe.db.exists("Affiliate Click Log", aff_cookie_parts[-1])

    if not click_log:
        return

    keyword = frappe.db.get_value("Affiliate Click Log", click_log, "keyword")
    return keyword
