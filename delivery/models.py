from django.db import models
from django.conf import settings

class DeliveryAgent(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_agent')
	vehicle_type = models.CharField(max_length=64)
	vehicle_reg = models.CharField(max_length=32)
	# Standard CharField for live tracking coordinates
	current_location = models.CharField(max_length=100, null=True, blank=True, help_text="Latitude,Longitude as text")
	is_online = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.user} ({self.vehicle_type})"

class DeliveryAssignment(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("picked_up", "Picked Up"),
		("delivering", "Delivering"),
		("delivered", "Delivered"),
		("cancelled", "Cancelled"),
	]
	sub_order = models.OneToOneField('orders.SubOrder', on_delete=models.CASCADE, related_name='delivery_assignment')
	agent = models.ForeignKey(DeliveryAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
	pickup_time = models.DateTimeField(null=True, blank=True)
	delivery_time = models.DateTimeField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

	def __str__(self):
		return f"Delivery for {self.sub_order} - {self.status}"
