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

    frappe.db.commit()  # nosemgrep
