# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AffiliateReferral(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amount: DF.Currency
        comment: DF.SmallText | None
        date: DF.Date | None
        is_manual: DF.Check
        keyword: DF.Link | None
        payment_entry: DF.Link | None
        record_type: DF.Literal["referral", "void"]  # noqa: F821
        sales_partner: DF.Link | None
        tier: DF.Int
        void: DF.Check
        void_affiliate_referral: DF.Link | None
    # end: auto-generated types

    def validate(self):
        db_is_void = frappe.db.get_value("Affiliate Referral", self.name, "void")
        if db_is_void != self.void:
            if self.void:
                frappe.enqueue(
                    method=self.make_void,
                    queue="short",
                    job_name=f"Make Affiliate Referral {self.name} Void",
                )

    def make_void(self):
        linked_referrals = frappe.get_all(
            "Affiliate Referral",
            filters={
                "record_type": "referral",
                "void": 0,
                "payment_entry": self.payment_entry,
            },
            fields=["name"],
        )
        self.make_void_referral(self.name)
        for referral in linked_referrals:
            # Note: Using frappe.db.set_value here to avoid recursion while updating linked referrals
            frappe.db.set_value("Affiliate Referral", referral.name, "void", 1)
            self.make_void_referral(referral.name)

    def make_void_referral(self, referral_name):
        if self.name != referral_name:
            referral_doc = frappe.get_doc("Affiliate Referral", referral_name)
        else:
            referral_doc = self
        new_void_doc = frappe.new_doc("Affiliate Referral")
        new_void_doc.update(
            {
                "sales_partner": referral_doc.sales_partner,
                "record_type": "void",
                "void_affiliate_referral": referral_name,
                "amount": referral_doc.amount,
                "keyword": referral_doc.keyword,
                "date": frappe.utils.getdate(),
                "payment_entry": referral_doc.payment_entry,
                "tier": referral_doc.tier,
            }
        )
        new_void_doc.insert()
