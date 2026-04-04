from django.db import models


class Medication(models.Model):
	name = models.CharField(max_length=255, db_index=True)
	generic_name = models.CharField(max_length=255, blank=True)
	description = models.TextField(blank=True)
	dosage = models.CharField(max_length=255, blank=True)
	manufacturer = models.CharField(max_length=255, blank=True)
	active_ingredients = models.TextField(blank=True)
	rx_required = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	mechanism = models.TextField(blank=True, null=True, help_text="Jinsi dawa inavyofanya kazi")
	side_effects = models.JSONField(blank=True, null=True, help_text="Orodha ya madhara ya kawaida")
	faqs = models.JSONField(blank=True, null=True, help_text="Maswali na majibu (Q&A)")
	doctor_advice = models.TextField(blank=True, null=True, help_text="Ushauri wa daktari")
	did_you_know = models.TextField(blank=True, null=True, help_text="Fact ya haraka kuhusu dawa")

	@property
	def side_effects_list(self):
		return self.side_effects or []

	@property
	def faqs_list(self):
		if self.faqs:
			return [(q.get('q'), q.get('a')) for q in self.faqs]
		return []
	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name

	def to_dict(self):
		return {
			'id': self.id,
			'name': self.name,
			'generic_name': self.generic_name,
			'description': self.description,
			'dosage': self.dosage,
			'manufacturer': self.manufacturer,
			'active_ingredients': self.active_ingredients,
			'rx_required': self.rx_required,
			'created_at': self.created_at.isoformat() if self.created_at else None,
			'updated_at': self.updated_at.isoformat() if self.updated_at else None,
		}
