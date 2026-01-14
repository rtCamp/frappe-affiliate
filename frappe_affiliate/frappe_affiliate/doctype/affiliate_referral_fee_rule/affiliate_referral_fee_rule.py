# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AffiliateReferralFeeRule(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from frappe_affiliate.frappe_affiliate.doctype.referral_rule_item_code.referral_rule_item_code import (
            ReferralRuleItemCode,
        )
        from frappe_affiliate.frappe_affiliate.doctype.referral_user_group.referral_user_group import (
            ReferralUserGroup,
        )

        apply_except_item_code: DF.Table[ReferralRuleItemCode]
        apply_on_group: DF.Table[ReferralUserGroup]
        apply_on_item_code: DF.Table[ReferralRuleItemCode]
        comment: DF.Data | None
        disabled: DF.Check
        first_referral_rate: DF.Percent
        priority: DF.Int
        subsequent_referral_rate: DF.Percent
    # end: auto-generated types

    def validate(self):
        if self.first_referral_rate > 100 or self.subsequent_referral_rate > 100:
            frappe.throw(_("Referral rates must be between 0 and 100."))

        groups = self.apply_on_group
        if groups:
            for group in groups:
                group_exists = frappe.db.exists("User Group", group.user_group)
                if not group_exists:
                    frappe.throw(
                        _("User Group {0} does not exist").format(group.user_group)
                    )
