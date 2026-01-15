# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AffiliateLeadLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        banner_id: DF.Link | None
        first_visited: DF.Datetime | None
        keyword: DF.Link | None
        referrer: DF.SmallText | None
        remote_address: DF.Data | None
        sales_partner: DF.Link
        time: DF.Datetime | None
        user: DF.Link
    # end: auto-generated types

    pass
