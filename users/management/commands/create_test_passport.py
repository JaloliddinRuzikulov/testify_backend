from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from users.passport_models import PassportData
import base64


class Command(BaseCommand):
    help = 'Creates test passport data for development'

    def handle(self, *args, **kwargs):
        # Sample base64 image (1x1 pixel transparent PNG for demo)
        # In production, this would be actual passport photos
        sample_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        test_passports = [
            {
                'passport_series': 'AA',
                'passport_number': '1234567',
                'pinfl': '12345678901234',
                'first_name': 'Test',
                'last_name': 'User',
                'middle_name': 'Admin',
                'birth_date': date(1990, 1, 1),
                'address': 'Toshkent shahar, Yunusobod tumani',
                'issued_by': "O'zbekiston Respublikasi IIB",
                'issue_date': date(2020, 1, 1),
                'expire_date': date(2030, 1, 1),
            },
            {
                'passport_series': 'AB',
                'passport_number': '2345678',
                'pinfl': '23456789012345',
                'first_name': 'Creator',
                'last_name': 'Test',
                'middle_name': 'User',
                'birth_date': date(1995, 5, 15),
                'address': 'Samarqand viloyati, Samarqand shahar',
                'issued_by': "O'zbekiston Respublikasi IIB",
                'issue_date': date(2021, 3, 15),
                'expire_date': date(2031, 3, 15),
            },
            {
                'passport_series': 'AC',
                'passport_number': '3456789',
                'pinfl': '34567890123456',
                'first_name': 'Expert',
                'last_name': 'Demo',
                'middle_name': 'Test',
                'birth_date': date(1988, 10, 20),
                'address': 'Buxoro viloyati, Buxoro shahar',
                'issued_by': "O'zbekiston Respublikasi IIB",
                'issue_date': date(2019, 6, 1),
                'expire_date': date(2029, 6, 1),
            },
        ]
        
        for passport_data in test_passports:
            passport, created = PassportData.objects.get_or_create(
                pinfl=passport_data['pinfl'],
                defaults={
                    **passport_data,
                    'photo_base64': sample_image_base64
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created passport: {passport.passport_series}{passport.passport_number} - "
                        f"{passport.first_name} {passport.last_name} (PINFL: {passport.pinfl})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Passport already exists: {passport.passport_series}{passport.passport_number}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('\nTest passport data created successfully!'))
        self.stdout.write(self.style.SUCCESS('You can now use these PINFLs for testing:'))
        self.stdout.write('  - 12345678901234 (Admin Test User)')
        self.stdout.write('  - 23456789012345 (Creator Test)')
        self.stdout.write('  - 34567890123456 (Expert Demo)')