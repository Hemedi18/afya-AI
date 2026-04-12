from django.db import models
from django.conf import settings
from decimal import Decimal

class Pharmacy(models.Model):
	name = models.CharField(max_length=255)
	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_pharmacies')
	license_number = models.CharField(max_length=100, unique=True)
	is_verified = models.BooleanField(default=False)
	is_open_24_7 = models.BooleanField(default=False)
	image = models.ImageField(upload_to='pharmacies/', null=True, blank=True)
	is_active = models.BooleanField(default=True)
	phone_number = models.CharField(max_length=20, blank=True)
	email = models.EmailField(blank=True)
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
	wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
	rating = models.FloatField(default=0.0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def city(self):
		return self.location.city if hasattr(self, 'location') else "Unknown"

	def __str__(self):
		return self.name

class PharmacyLocation(models.Model):
	pharmacy = models.OneToOneField(Pharmacy, on_delete=models.CASCADE, related_name='location')
	address = models.CharField(max_length=255)
	city = models.CharField(max_length=100)
	# Standard CharField for storing "Lat,Lon" to avoid GIS dependencies in SQLite
	location = models.CharField(max_length=100, help_text="Latitude,Longitude as text", null=True, blank=True)
	delivery_radius_km = models.FloatField(default=5.0)

	def __str__(self):
		return f"{self.pharmacy.name} - {self.address}, {self.city}"

class PharmacyStaff(models.Model):
	ROLE_CHOICES = [
		("manager", "Manager"),
		("pharmacist", "Pharmacist"),
	]
	pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='staff')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user} - {self.role} @ {self.pharmacy}"
