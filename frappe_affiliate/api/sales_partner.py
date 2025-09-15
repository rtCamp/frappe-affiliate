import frappe


@frappe.whitelist()
def get_all_affiliates():
    affiliates = frappe.get_list(
        "Sales Partner",
        fields=["name", "custom_user"],
    )

    return affiliates
