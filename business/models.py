
from django.db import models

class Pharmacy(models.Model):
	name = models.CharField(max_length=255)
	address = models.CharField(max_length=512)
	latitude = models.FloatField()
	longitude = models.FloatField()
	contact_phone = models.CharField(max_length=32, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name

class Drug(models.Model):
	name = models.CharField(max_length=255)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='drugs')
	stock = models.PositiveIntegerField(default=0)
	description = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.name} ({self.pharmacy.name})"
