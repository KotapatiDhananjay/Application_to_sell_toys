from decimal import Decimal

from django.test import TestCase

from apps.core.factories import make_product, make_user
from apps.orders.exceptions import InvalidStatusTransition
from apps.orders.models import Order, OrderItem, Payment

S = Order.Status


def make_order(user=None, **kwargs):
    data = dict(
        user=user or make_user(), shipping_name="Sam Buyer", shipping_phone="+15551234567",
        shipping_line1="1 Toy Lane", shipping_city="Springfield", shipping_state="IL",
        shipping_postal_code="62701", shipping_country="USA", total=Decimal("40.00"),
    )
    data.update(kwargs)
    return Order.objects.create(**data)


class OrderNumberTests(TestCase):
    def test_number_is_generated_and_formatted(self):
        order = make_order()
        self.assertRegex(order.order_number, r"^TOY-\d{8}-[A-Z0-9]{6}$")

    def test_numbers_are_unique(self):
        numbers = {make_order().order_number for _ in range(25)}
        self.assertEqual(len(numbers), 25)

    def test_number_is_stable_across_saves(self):
        order = make_order()
        number = order.order_number
        order.customer_note = "Gift wrap please"
        order.save()
        self.assertEqual(Order.objects.get(pk=order.pk).order_number, number)


class OrderStatusTests(TestCase):
    def setUp(self):
        self.order = make_order()
        self.admin = make_user()

    def test_default_status_is_placed(self):
        self.assertEqual(self.order.status, S.PLACED)

    def test_happy_path_to_delivered_records_history(self):
        for status in [S.CONFIRMED, S.PACKED, S.SHIPPED, S.OUT_FOR_DELIVERY, S.DELIVERED]:
            self.order.set_status(status, user=self.admin)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, S.DELIVERED)
        history = list(self.order.status_history.values_list("status", flat=True))
        self.assertEqual(history, ["confirmed", "packed", "shipped", "out_for_delivery", "delivered"])
        self.assertEqual(self.order.status_history.first().changed_by, self.admin)

    def test_cannot_skip_steps(self):
        with self.assertRaises(InvalidStatusTransition):
            self.order.set_status(S.SHIPPED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, S.PLACED)
        self.assertEqual(self.order.status_history.count(), 0)

    def test_terminal_states_cannot_change(self):
        self.order.set_status(S.CANCELLED)
        with self.assertRaises(InvalidStatusTransition):
            self.order.set_status(S.CONFIRMED)

    def test_cannot_cancel_after_shipping(self):
        for status in [S.CONFIRMED, S.PACKED, S.SHIPPED]:
            self.order.set_status(status)
        self.assertFalse(self.order.can_transition_to(S.CANCELLED))

    def test_customer_can_cancel_only_early(self):
        self.assertTrue(self.order.is_customer_cancellable)
        self.order.set_status(S.CONFIRMED)
        self.assertTrue(self.order.is_customer_cancellable)
        self.order.set_status(S.PACKED)
        self.assertFalse(self.order.is_customer_cancellable)

    def test_every_status_has_a_transition_rule(self):
        self.assertEqual(set(Order.ALLOWED_TRANSITIONS), set(S))


class OrderItemAndPaymentTests(TestCase):
    def test_item_snapshot_survives_product_deletion(self):
        order = make_order()
        product = make_product(name="Robot Kit", price=Decimal("30.00"))
        item = OrderItem.objects.create(
            order=order, product=product, product_name=product.name, sku=product.sku,
            list_price=product.price, unit_price=Decimal("27.00"), quantity=2,
        )
        self.assertEqual(item.line_total, Decimal("54.00"))
        product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, "Robot Kit")

    def test_is_paid_reflects_successful_payment(self):
        order = make_order()
        self.assertFalse(order.is_paid)
        Payment.objects.create(order=order, method="card", amount=order.total,
                               status=Payment.Status.FAILED, transaction_id="MOCK-1")
        self.assertFalse(order.is_paid)
        Payment.objects.create(order=order, method="card", amount=order.total,
                               status=Payment.Status.SUCCESS, transaction_id="MOCK-2")
        self.assertTrue(order.is_paid)

    def test_order_survives_but_user_is_protected(self):
        from django.db.models import ProtectedError
        order = make_order()
        with self.assertRaises(ProtectedError):
            order.user.delete()