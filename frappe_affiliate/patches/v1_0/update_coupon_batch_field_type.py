import frappe
from frappe.model.meta import get_table_columns


def execute():
    try:
        columns_to_drop = ["code_length", "coupons_count"]

        # Get current columns in the table
        current_columns = get_table_columns("Coupon Batch")

        for column in columns_to_drop:
            if column in current_columns:
                frappe.db.sql("ALTER TABLE `tabCoupon Batch` DROP COLUMN %s", (column))
        # frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_coupon_batch_field_type")
        print(f"Error occurred: {e}")
