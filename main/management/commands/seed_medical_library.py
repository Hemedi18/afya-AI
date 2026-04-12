from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files import File
from django.conf import settings
import os
import random
from datetime import timedelta
from django.utils import timezone

from pharmacy.models import Pharmacy, PharmacyLocation
from inventory.models import MedicineTemplate, PharmacyStock


class Command(BaseCommand):
    help = 'Seed test data: 10 pharmacies, each with 100 medicines (random prices, categories, manufacturers)'


    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing Pharmacy, PharmacyLocation, MedicineTemplate, and PharmacyStock records before seeding sample data.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # Create a test owner if not exists
        owner, created = User.objects.get_or_create(username='pharmacy_owner', defaults={'email': 'owner@example.com'})
        if created:
            owner.set_password('testpass123')
            owner.save()
            self.stdout.write(self.style.SUCCESS('Created default pharmacy owner: pharmacy_owner'))

        pharmacy_image_path = os.path.join(settings.BASE_DIR, 'assests', 'afyafinalicon.jpg')
        medicine_image_path = os.path.join(settings.BASE_DIR, 'assests', 'doctur.png')

        if not os.path.exists(pharmacy_image_path):
            self.stdout.write(self.style.WARNING(f"Pharmacy image not found at: {pharmacy_image_path}. Seeding without images."))
        if not os.path.exists(medicine_image_path):
            self.stdout.write(self.style.WARNING(f"Medicine image not found at: {medicine_image_path}. Seeding without images."))

        if options.get('reset'):
            self.stdout.write(self.style.WARNING('Clearing existing pharmacy and inventory data...'))
            PharmacyStock.objects.all().delete()
            MedicineTemplate.objects.all().delete()
            PharmacyLocation.objects.all().delete()
            Pharmacy.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        pharmacies_to_create = 10
        medicines_per_pharmacy = 100
        total_medicines = 100 # Create 100 unique medicine templates

        # --- Create Pharmacies ---
        self.stdout.write(self.style.MIGRATE_HEADING(f'Creating {pharmacies_to_create} pharmacies...'))
        pharmacies = []
        for i in range(1, pharmacies_to_create + 1):
            pharmacy = Pharmacy.objects.create(
                name=f'Pharmacy Health Node {i}',
                owner=owner,
                license_number=f'LIC-{random.randint(10000, 99999)}-{i}',
                is_verified=random.choice([True, False]),
                is_open_24_7=True,
                phone_number=f'+255-700-{i:03d}',
                email=f'pharmacy{i}@afyasmart.com',
            )
            if os.path.exists(pharmacy_image_path) and os.path.isfile(pharmacy_image_path):
                with open(pharmacy_image_path, 'rb') as f:
                    pharmacy.image.save(os.path.basename(pharmacy_image_path), File(f), save=True)
            
            PharmacyLocation.objects.create(
                pharmacy=pharmacy,
                address=f'Block {i}, Medical District',
                city=random.choice(['Dar es Salaam', 'Arusha', 'Mwanza', 'Dodoma']),
                location=f'{random.uniform(-10, -5):.6f},{random.uniform(35, 40):.6f}', # Random Tanzania coords
                delivery_radius_km=random.uniform(3.0, 15.0)
            )
            pharmacies.append(pharmacy)

        # --- Create Medicine Templates ---
        self.stdout.write(self.style.MIGRATE_HEADING(f'Creating {total_medicines} unique medicine templates...'))
        medicine_templates = []
        medicine_categories = ['Pain Relief', 'Antibiotic', 'Antifungal', 'Antiviral', 'Vitamins', 'Allergy', 'Digestive', 'Cold & Flu', 'Dermatology', 'Cardiovascular']
        medicine_brands = ['MediBrand', 'HealthCo', 'PharmaGen', 'BioCure', 'WellMed']
        
        for i in range(1, total_medicines + 1):
            generic_name = f'{random.choice(["Generic", "Advanced", "Fast-Act"])} {random.choice(medicine_categories)} {i}'
            brand_name = f'{random.choice(medicine_brands)} {random.choice(["Plus", "Max", "Care"])}'
            category = random.choice(medicine_categories)
            requires_prescription = random.choice([True, False, False]) # More non-prescription for variety
            
            medicine = MedicineTemplate.objects.create(
                generic_name=generic_name,
                brand=brand_name,
                category=category,
                description=f'Effective for {category.lower()} conditions. Consult a doctor if symptoms persist.',
                requires_prescription=requires_prescription,
                side_effects='Mild dizziness, nausea, or drowsiness. Read leaflet for full details.',
            )
            if os.path.exists(medicine_image_path) and os.path.isfile(medicine_image_path):
                with open(medicine_image_path, 'rb') as f:
                    medicine.image.save(os.path.basename(medicine_image_path), File(f), save=True)
            medicine_templates.append(medicine)
            self.stdout.write(f'  Created Medicine Template: {medicine.generic_name}')
            
        # --- Create Pharmacy Stock for each Pharmacy ---
        self.stdout.write(self.style.MIGRATE_HEADING('Stocking pharmacies with medicines...'))
        for pharmacy in pharmacies:
            self.stdout.write(f'  Stocking {pharmacy.name}...')
            for i in range(medicines_per_pharmacy):
                medicine = random.choice(medicine_templates) # Randomly assign from all templates
                price = round(random.uniform(5000, 75000), 2)
                quantity = random.randint(10, 250)
                expiry_date = timezone.now().date() + timedelta(days=random.randint(90, 730)) # 3 months to 2 years
                
                PharmacyStock.objects.create(
                    pharmacy=pharmacy,
                    medicine=medicine,
                    price=price,
                    quantity=quantity,
                    low_stock_threshold=random.randint(5, 20),
                    batch_number=f'BATCH-{pharmacy.id}-{medicine.id}-{random.randint(100, 999)}',
                    expiry_date=expiry_date,
                    is_active=True
                )
            self.stdout.write(f'    {medicines_per_pharmacy} medicines stocked for {pharmacy.name}.')

        self.stdout.write(self.style.SUCCESS('\n✅ Pharmacy and Inventory seed complete.'))
        self.stdout.write(self.style.WARNING('Remember to run: python manage.py makemigrations inventory && python manage.py migrate'))
