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


def apply_referral_fee_rules(doc):
    if not doc.sales_partner or doc.sales_partner == "":
        return
    invoice_item_codes = set(item.item_code for item in doc.items)
    referral_fee_rules = frappe.get_all(
        "Affiliate Referral Fee Rule", filters={"disabled": 0}, fields=["name"]
    )

    referral_fee_rule = None

    invoice_count = get_invoice_count(doc)

    sales_partner = doc.sales_partner
    sales_partner_user = frappe.db.get_value(
        "Sales Partner", sales_partner, "custom_user"
    )
    affiliate_user_group = frappe.get_all(
        "User Group Member", filters={"user": sales_partner_user}, pluck="parent"
    )

    for rule in referral_fee_rules:
        rule_doc = frappe.get_doc("Affiliate Referral Fee Rule", rule.name)
        apply_on_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_on_item_code
        )
        apply_except_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_except_item_code
        )
        apply_on_group = [
            referral_group.user_group for referral_group in rule_doc.apply_on_group
        ]
        if (
            (
                len(rule_doc.apply_on_item_code) == 0
                or invoice_item_codes.issubset(apply_on_rule_item_codes)
            )
            and not invoice_item_codes.intersection(apply_except_rule_item_codes)
            and (
                apply_on_group is None
                or len(apply_on_group) == 0
                or set(apply_on_group).intersection(affiliate_user_group)
            )
        ):
            if referral_fee_rule:
                if rule_doc.priority < referral_fee_rule.priority:
                    referral_fee_rule = rule_doc
            else:
                referral_fee_rule = rule_doc
            referral_fee_rule = rule_doc

    referral_fee_rate = None
    if referral_fee_rule:
        if invoice_count < 1:
            referral_fee_rate = (
                referral_fee_rule.get("first_referral_rate", None)
                or frappe.get_single("Affiliate Settings").first_referral_rate
            )
        else:
            referral_fee_rate = (
                referral_fee_rule.get("subsequent_referral_rate", None)
                or frappe.get_single("Affiliate Settings").subsequent_referral_rate
            )
        doc.custom_affiliate_referral_fee_rule = referral_fee_rule.name

    if not referral_fee_rate:
        referral_fee_rate = (
            frappe.db.get_value("Sales Partner", doc.sales_partner, "commission_rate")
            or 0
        )

    return referral_fee_rate
