from django.db import models
from decimal import Decimal
from django.utils import timezone

class MedicineTemplate(models.Model):
    generic_name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='medicines/', null=True, blank=True)
    brand = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_prescription = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    side_effects = models.TextField(blank=True)

    def __str__(self):
        return f"{self.generic_name} ({self.brand})"

class PharmacyStock(models.Model):
    pharmacy = models.ForeignKey('pharmacy.Pharmacy', on_delete=models.CASCADE, related_name='stocks')
    medicine = models.ForeignKey(MedicineTemplate, on_delete=models.CASCADE, related_name='pharmacy_stocks')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    low_stock_threshold = models.PositiveIntegerField(default=5)
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    def __str__(self):
        return f"{self.medicine} @ {self.pharmacy} (Batch: {self.batch_number})"
