from django.contrib import admin, messages

from .exceptions import InvalidStatusTransition
from .models import Order, OrderItem, OrderStatusHistory, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "sku", "list_price", "unit_price", "quantity")
    can_delete = False


class StatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("status", "note", "changed_by", "created_at")
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("method", "status", "amount", "provider", "transaction_id")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "user__email", "shipping_name")
    readonly_fields = ("order_number", "subtotal", "discount_total", "shipping_fee", "total")
    inlines = [OrderItemInline, PaymentInline, StatusHistoryInline]

    def save_model(self, request, obj, form, change):
        """Route status edits through Order.set_status() so the workflow rules
        are enforced and the tracking history is written."""
        if change and "status" in form.changed_data:
            new_status, obj.status = obj.status, form.initial["status"]
            try:
                obj.set_status(new_status, user=request.user, note="Changed in Django admin")
            except InvalidStatusTransition as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        super().save_model(request, obj, form, change)