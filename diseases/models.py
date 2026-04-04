from django.db import models


class Disease(models.Model):
	name = models.CharField(max_length=255, db_index=True)
	icd_code = models.CharField(max_length=100, blank=True)
	definition = models.TextField(blank=True)
	symptoms = models.TextField(blank=True)
	prevention = models.TextField(blank=True)
	treatment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	complications = models.JSONField(blank=True, null=True, help_text="Orodha ya madhara/matatizo yanayoweza kutokea")
	faqs = models.JSONField(blank=True, null=True, help_text="Maswali na majibu (Q&A)")
	doctor_advice = models.TextField(blank=True, null=True, help_text="Ushauri wa daktari")
	did_you_know = models.TextField(blank=True, null=True, help_text="Fact ya haraka kuhusu ugonjwa")

	@property
	def complications_list(self):
		return self.complications or []

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
			'icd_code': self.icd_code,
			'definition': self.definition,
			'symptoms': self.symptoms,
			'prevention': self.prevention,
			'treatment': self.treatment,
			'created_at': self.created_at.isoformat() if self.created_at else None,
			'updated_at': self.updated_at.isoformat() if self.updated_at else None,
		}
