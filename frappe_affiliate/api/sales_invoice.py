import frappe


def get_purchase_count(customer, coupon_code, subscription):
    count = frappe.db.count(
        "Sales Invoice",
        {
            "customer": customer,
            "coupon_code": coupon_code,
            "subscription": subscription,
            "docstatus": 1,
        },
    )
    return count


def get_invoice_count(doc):
    count = frappe.db.count(
        "Sales Invoice",
        {"customer": doc.customer, "subscription": doc.subscription, "docstatus": 1},
    )
    return count


def apply_commission_rules(doc):
    invoice_item_codes = set(item.item_code for item in doc.items)
    commission_rules = frappe.get_all(
        "Affiliate Commission Rule", filters={"disabled": 0}, fields=["name"]
    )

    commission_rule = None

    invoice_count = get_invoice_count(doc)

    for rule in commission_rules:
        rule_doc = frappe.get_doc("Affiliate Commission Rule", rule.name)
        rule_item_codes = set(child.item_code for child in rule_doc.item_code)
        if invoice_item_codes.issubset(rule_item_codes):
            commission_rule = rule_doc
            break

    commission_percent = None
    if commission_rule:
        if invoice_count > 1:
            commission_percent = (
                commission_rule.get("first_commission", None)
                or frappe.get_single("Affiliate Settings").first_commission_rate
            )
        else:
            commission_percent = (
                commission_rule.get("subsequent_commission", None)
                or frappe.get_single("Affiliate Settings").subsequent_commission_rate
            )

    if not commission_percent:
        commission_percent = (
            frappe.db.get_value("Sales Partner", doc.sales_partner, "commission_rate")
            or 0
        )

    return commission_percent
