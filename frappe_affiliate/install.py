import frappe


def after_install():
    if not frappe.db.exists("Supplier Group", "Sales Partner"):
        frappe.get_doc(
            {
                "doctype": "Supplier Group",
                "supplier_group_name": "Sales Partner",
                "is_group": 0,
            }
        ).insert()

    if not frappe.db.exists("Sales Partner Type", "Affiliate"):
        frappe.get_doc(
            {"doctype": "Sales Partner Type", "sales_partner_type": "Affiliate"}
        ).insert()
    if not frappe.db.exists("User Group", "Affiliate Tier 1"):
        frappe.get_doc(
            {"doctype": "User Group", "__newname": "Affiliate Tier 1"}
        ).insert(ignore_mandatory=True)
    if not frappe.db.exists("User Group", "Affiliate Tier 2"):
        frappe.get_doc(
            {"doctype": "User Group", "__newname": "Affiliate Tier 2"}
        ).insert(ignore_mandatory=True)

    # nosemgrep
    frappe.db.commit()
