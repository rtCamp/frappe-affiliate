import frappe


def before_insert(doc, method=None):
    if not doc.partner_type == "Affiliate":
        return
    if doc.custom_user:
        username = frappe.db.get_value("User", doc.custom_user, "username")
        route_path = frappe.get_single_value(
            "Affiliate Settings", "affiliate_route_path"
        )
        doc.custom_affiliate_link = frappe.utils.get_url(route_path + username)


def after_insert(doc, method=None):
    if not doc.partner_type == "Affiliate":
        return
    supplier = frappe.get_doc(
        {
            "doctype": "Supplier",
            "custom_sales_partner": doc.name,
            "supplier_name": doc.partner_name,
            "supplier_type": "Individual",
            "supplier_group": "Sales Partner",
        }
    )
    supplier.insert(ignore_permissions=True)
