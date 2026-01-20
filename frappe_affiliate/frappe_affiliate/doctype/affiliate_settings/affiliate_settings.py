# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AffiliateSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from frappe_affiliate.frappe_affiliate.doctype.affiliate_banner_and_text_link.affiliate_banner_and_text_link import (
            AffiliateBannerandTextLink,
        )
        from frappe_affiliate.frappe_affiliate.doctype.referral_user_group.referral_user_group import (
            ReferralUserGroup,
        )

        affiliate_redirect_url: DF.Data
        affiliate_registration_email: DF.Link | None
        affiliate_route_path: DF.Data
        banner_and_text_link: DF.Table[AffiliateBannerandTextLink]
        banner_and_text_link_route_path: DF.Data
        cookie_timeout: DF.Int
        delay_payout_days: DF.Int
        enable_keywords_support: DF.Check
        enable_tier_2: DF.Check
        enable_tier_3: DF.Check
        first_referral_rate: DF.Percent
        intro_text_on_affiliate_info_page: DF.HTMLEditor | None
        minimum_payout: DF.Int
        subsequent_referral_rate: DF.Percent
        tier_2_groups: DF.Table[ReferralUserGroup]
        tier_3_groups: DF.Table[ReferralUserGroup]
    # end: auto-generated types

    pass
