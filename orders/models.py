from django.db import models
from django.conf import settings

class Order(models.Model):
	PAYMENT_STATUS_CHOICES = [
		("pending", "Pending"),
		("paid", "Paid"),
		("failed", "Failed"),
		("refunded", "Refunded"),
	]
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ecom_orders')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
	shipping_address = models.TextField(help_text="Full delivery address or instructions", default="")
	# Store coordinates for delivery calculation
	shipping_coords = models.CharField(max_length=100, blank=True, null=True, help_text="Lat,Lon text for fallback")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Main Order #{self.id} - {self.user.username}"

class SubOrder(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending Approval"),
		("confirmed", "Confirmed by Pharmacy"),
		("processing", "Packing Items"),
		("ready", "Ready for Pickup"),
		("shipped", "In Transit"),
		("delivered", "Delivered"),
		("cancelled", "Cancelled"),
	]
	main_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='suborders')
	pharmacy = models.ForeignKey('pharmacy.Pharmacy', on_delete=models.CASCADE, related_name='order_segments')
	sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	commission_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"SubOrder #{self.id} - {self.pharmacy.name}"

class OrderItem(models.Model):
	sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name='items', null=True, blank=True)
	stock_item = models.ForeignKey('inventory.PharmacyStock', on_delete=models.PROTECT, related_name='order_entries', null=True, blank=True)
	quantity = models.PositiveIntegerField()
	price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

	def __str__(self):
		return f"{self.quantity}x {self.stock_item.medicine.generic_name}"
