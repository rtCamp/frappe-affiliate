import frappe


def is_user_affiliate(sales_partner):
    if not sales_partner:
        return {"is_affiliate": False}
    sales_partner = frappe.db.exists(
        "Sales Partner",
        {"name": sales_partner, "custom_disabled": 0, "custom_banned": 0},
    )
    if sales_partner:
        return {
            "is_affiliate": True,
            "sales_partner": sales_partner,
        }
    else:
        return {"is_affiliate": False}
