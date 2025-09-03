from datetime import date

from erpnext.accounts.doctype.subscription.subscription import Subscription

DateTimeLikeObject = str | date


class SubscriptionOverride(Subscription):
    def create_invoice(
        self,
        from_date: DateTimeLikeObject | None = None,
        to_date: DateTimeLikeObject | None = None,
        posting_date: DateTimeLikeObject | None = None,
    ):
        invoice = super().create_invoice(from_date, to_date, posting_date)
        invoice.reload()

        if self.get("custom_coupon_code", None):
            invoice.coupon_code = self.custom_coupon_code
            invoice.save()

        return invoice
