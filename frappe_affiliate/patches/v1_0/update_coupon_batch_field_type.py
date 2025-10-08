import frappe
from frappe.model.meta import get_table_columns


def execute():
    columns_to_drop = ["code_length", "coupons_count"]

    # Get current columns in the table
    current_columns = get_table_columns("Coupon Batch")

    for column in columns_to_drop:
        if column in current_columns:
            frappe.db.sql(f"ALTER TABLE `tabCoupon Batch` DROP COLUMN `{column}`")
    frappe.db.commit()
