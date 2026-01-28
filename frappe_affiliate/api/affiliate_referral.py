import frappe
from frappe import _
from frappe.utils import getdate

from frappe_affiliate.utils.sales_partner import is_user_affiliate


@frappe.whitelist(methods=["POST"])
def insert_manual_affiliate_referral(
    affiliate: str,
    amount: float,
    date: str,
    comment: str | None = None,
) -> str:
    """
    Inserts a manual affiliate referral for a given sales invoice and sales partner.

    Params:
        affiliate: The sales partner (affiliate) for whom the referral is being recorded.
        amount: The amount for the affiliate referral.
        date: The date of the referral.
        comment: An optional comment for the referral.
    """
    if not amount or amount <= 0:
        frappe.throw(_("Amount must be a positive number."))

    if not affiliate:
        frappe.throw(_("Affiliate is required."))

    if not is_user_affiliate(affiliate).get("is_affiliate"):
        frappe.throw(_("The provided user is not a valid affiliate."))

    new_referral = frappe.new_doc("Affiliate Referral")
    new_referral.sales_partner = affiliate
    new_referral.amount = amount
    new_referral.comment = comment
    new_referral.record_type = "referral"
    new_referral.is_manual = 1
    new_referral.date = getdate(date)
    new_referral.insert()

    return new_referral.name
