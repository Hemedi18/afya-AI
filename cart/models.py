from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as geomodels

class Cart(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Cart({self.user})"

class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	stock = models.ForeignKey('inventory.PharmacyStock', on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField()

	def __str__(self):
		return f"{self.quantity} x {self.stock}"

class Order(models.Model):
	PAYMENT_STATUS_CHOICES = [
		("pending", "Pending"),
		("paid", "Paid"),
		("failed", "Failed"),
		("refunded", "Refunded"),
	]
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_orders')
	total_amount = models.DecimalField(max_digits=12, decimal_places=2)
	payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
	# For SQLite compatibility, store as text (e.g., 'lat,lon')
	shipping_address = models.CharField(max_length=100, help_text="Latitude,Longitude as text")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Order #{self.id} by {self.user}"

class SubOrder(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("confirmed", "Confirmed"),
		("processing", "Processing"),
		("ready", "Ready for Delivery"),
		("delivered", "Delivered"),
		("cancelled", "Cancelled"),
	]
	main_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='suborders')
	pharmacy = models.ForeignKey('pharmacy.Pharmacy', on_delete=models.CASCADE, related_name='suborders')
	sub_total = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"SubOrder #{self.id} for {self.pharmacy}"


class OrderItem(models.Model):
	sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name='items')
	stock_item = models.ForeignKey('inventory.PharmacyStock', on_delete=models.CASCADE, related_name='cart_order_items')
	quantity = models.PositiveIntegerField()
	price_at_time_of_purchase = models.DecimalField(max_digits=10, decimal_places=2)

	def __str__(self):
		return f"{self.quantity} x {self.stock_item}"
from django.db import models

# Create your models here.
