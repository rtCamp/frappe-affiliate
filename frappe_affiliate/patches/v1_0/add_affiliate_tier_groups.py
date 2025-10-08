import frappe


def execute():
    if not frappe.db.exists("User Group", "Affiliate Tier 1"):
        frappe.get_doc(
            {"doctype": "User Group", "__newname": "Affiliate Tier 1"}
        ).insert(ignore_mandatory=True)
    if not frappe.db.exists("User Group", "Affiliate Tier 2"):
        frappe.get_doc(
            {"doctype": "User Group", "__newname": "Affiliate Tier 2"}
        ).insert(ignore_mandatory=True)
