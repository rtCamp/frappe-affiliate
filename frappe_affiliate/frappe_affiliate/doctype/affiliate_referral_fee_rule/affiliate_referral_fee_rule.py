# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AffiliateReferralFeeRule(Document):
    def validate(self):
        if self.first_referral_rate > 100 or self.subsequent_referral_rate > 100:
            frappe.throw(_("Referral rates must be between 0 and 100."))

        if self.apply_on_group:
            group_exists = frappe.db.exists("User Group", self.apply_on_group)
            if not group_exists:
                frappe.throw(
                    _("User Group {0} does not exist").format(self.apply_on_group)
                )
