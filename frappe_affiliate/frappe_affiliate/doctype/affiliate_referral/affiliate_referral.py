# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AffiliateReferral(Document):
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
                "record_type": "commission",
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
