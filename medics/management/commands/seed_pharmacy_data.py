from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pharmacy.models import Pharmacy
from inventory.models import Medicine, MedicineCategory, Stock, Manufacturer
import random

class Command(BaseCommand):
    help = 'Seed test data: 10 pharmacies, each with 100 medicines (random prices, categories, manufacturers)'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        # Create a test owner
        owner, _ = User.objects.get_or_create(username='pharmacy_owner', defaults={'email': 'owner@example.com'})
        owner.set_password('testpass123')
        owner.save()

        # Create categories and manufacturers
        categories = [
            MedicineCategory.objects.get_or_create(name=f'Category {i}', defaults={'description': f'Desc {i}'})[0]
            for i in range(1, 11)
        ]
        manufacturers = [
            Manufacturer.objects.get_or_create(name=f'Manufacturer {i}', country='CountryX')[0]
            for i in range(1, 11)
        ]

        # Create 10 pharmacies
        pharmacy_image_path = 'assests/afyafinalicon.jpg'
        medicine_image_path = 'assests/doctur.png'
        for p in range(1, 11):
            pharmacy, _ = Pharmacy.objects.get_or_create(
                name=f'Pharmacy {p}',
                owner=owner,
                defaults={
                    'license_number': f'LIC{p:04d}',
                    'license_document': '',
                    'phone': f'+255700000{p:02d}',
                    'email': f'pharmacy{p}@test.com',
                    'address': f'Street {p}',
                    'city': 'Dar es Salaam',
                    'country': 'Tanzania',
                    'is_verified': True,
                }
            )
            # Always set image to local asset
            pharmacy.image = pharmacy_image_path
            pharmacy.save()
            for m in range(1, 101):
                med, _ = Medicine.objects.get_or_create(
                    name=f'Medicine {p}-{m}',
                    generic_name=f'Gen {m}',
                    brand=f'Brand {random.randint(1, 20)}',
                    category=random.choice(categories),
                    manufacturer=random.choice(manufacturers),
                    defaults={
                        'description': f'Description for Medicine {p}-{m}',
                        'requires_prescription': random.choice([True, False]),
                    }
                )
                med.image = medicine_image_path
                med.save()
                price = round(random.uniform(1000, 50000), 2)
                Stock.objects.get_or_create(
                    pharmacy=pharmacy,
                    medicine=med,
                    defaults={
                        'price': price,
                        'quantity': random.randint(10, 200),
                        'expiry_date': '2027-12-31',
                        'batch_number': f'BATCH{p}{m:03d}'
                    }
                )
        self.stdout.write(self.style.SUCCESS('Seeded 10 pharmacies with 100 medicines each.'))
