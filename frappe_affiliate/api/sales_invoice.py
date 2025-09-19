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
    if not doc.sales_partner or doc.sales_partner == "":
        return
    invoice_item_codes = set(item.item_code for item in doc.items)
    commission_rules = frappe.get_all(
        "Affiliate Commission Rule", filters={"disabled": 0}, fields=["name"]
    )

    commission_rule = None

    invoice_count = get_invoice_count(doc)

    sales_partner = doc.sales_partner
    sales_partner_user = frappe.db.get_value(
        "Sales Partner", sales_partner, "custom_user"
    )
    affiliate_user_group = frappe.get_all(
        "User Group Member", filters={"user": sales_partner_user}, pluck="parent"
    )

    for rule in commission_rules:
        rule_doc = frappe.get_doc("Affiliate Commission Rule", rule.name)
        apply_on_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_on_item_code
        )
        apply_except_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_except_item_code
        )
        apply_on_group = rule.apply_on_group
        if (
            (
                len(rule_doc.apply_on_item_code) == 0
                or invoice_item_codes.issubset(apply_on_rule_item_codes)
            )
            and not invoice_item_codes.intersection(apply_except_rule_item_codes)
            and (
                apply_on_group == None
                or apply_on_group == ""
                or apply_on_group in affiliate_user_group
            )
        ):
            if commission_rule:
                if rule_doc.priority < commission_rule.priority:
                    commission_rule = rule_doc
            else:
                commission_rule = rule_doc
            commission_rule = rule_doc

    commission_percent = None
    if commission_rule:
        if invoice_count < 1:
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
