import frappe


def after_insert(doc, method=None):
    """
    This function is called after a Sales Partner document is inserted.
    It creates a new supplier with the same name as the Sales Partner.
    """
    supplier = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": doc.partner_name,
            "supplier_type": "Individual",
            "supplier_group": "Sales Partner",
        }
    )
    supplier.insert(ignore_permissions=True)
