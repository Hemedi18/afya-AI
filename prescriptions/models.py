from django.db import models
from django.conf import settings

class Prescription(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("approved", "Approved"),
		("rejected", "Rejected"),
	]
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
	file = models.FileField(upload_to='prescriptions/')
	order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
	uploaded_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
	verified_by = models.ForeignKey('pharmacy.PharmacyStaff', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_prescriptions')
	notes = models.TextField(blank=True)

	def __str__(self):
		return f"Prescription({self.user}, {self.uploaded_at})"
