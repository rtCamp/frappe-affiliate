# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AffiliateMarketingMaterial(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        description: DF.SmallText | None
        disabled: DF.Check
        material: DF.Attach
    # end: auto-generated types

    pass
