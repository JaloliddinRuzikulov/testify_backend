#!/usr/bin/env python
"""
Real admin user yaratish RUZIQULOV JALOLIDDIN uchun
Real government API ma'lumotlari bilan
"""

import os
import sys
import django
import requests
import json

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from users.models import User
from users.passport_models import UserProfile, PassportData

# Real ma'lumotlar
PNFL = "51304025740014"
PASSPORT = "AC1987867"
USERNAME = "jaloliddin_admin"
PASSWORD = "Admin@2024!"

print(f"Creating admin user with PNFL: {PNFL}, Passport: {PASSPORT}")

# 1. Government API'dan ma'lumot olish
url = f"http://imei_api.uzbmb.uz/compress?imie={PNFL}&ps={PASSPORT}"
print(f"Fetching from: {url}")

try:
    response = requests.get(url, verify=False, timeout=10)
    data = response.json()

    if data.get('status') == 1:
        passport_data = data.get('data', {})
        print(f"✅ Successfully fetched data for: {passport_data.get('sname')} {passport_data.get('fname')}")

        # 2. User yaratish
        user, created = User.objects.update_or_create(
            username=USERNAME,
            defaults={
                'email': 'jaloliddin@dtm.uz',
                'first_name': passport_data.get('fname', ''),
                'last_name': passport_data.get('sname', ''),
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'pnfl': PNFL,
                'passport': PASSPORT
            }
        )

        user.set_password(PASSWORD)
        user.save()
        print(f"✅ Admin user {'created' if created else 'updated'}: {USERNAME}")

        # 3. UserProfile yaratish
        profile, _ = UserProfile.objects.update_or_create(
            pnfl=int(PNFL),
            defaults={
                'user': user,
                'ps_ser': passport_data.get('ps_ser', ''),
                'ps_num': str(passport_data.get('ps_num', '')),
                'sname': passport_data.get('sname', ''),
                'fname': passport_data.get('fname', ''),
                'mname': passport_data.get('mname', ''),
                'birth_place': passport_data.get('birth_place', ''),
                'birth_date': passport_data.get('birth_date', ''),
                'birth_country': passport_data.get('birth_country', ''),
                'birth_country_id': passport_data.get('birth_country_id', 0),
                'livestatus': str(passport_data.get('livestatus', '0')),
                'nationality': passport_data.get('nationality', ''),
                'nationality_id': passport_data.get('nationality_id', 0),
                'sex': str(passport_data.get('sex', '1')),
                'doc_give_place': passport_data.get('doc_give_place', ''),
                'doc_give_place_id': passport_data.get('doc_give_place_id', 0),
                'matches_date_begin_document': passport_data.get('matches_date_begin_document', ''),
                'matches_date_end_document': passport_data.get('matches_date_end_document', ''),
                'photo': passport_data.get('photo', ''),
                'is_verified': True,
                'verified_at': timezone.now()
            }
        )
        print(f"✅ UserProfile created/updated")

        # 4. PassportData yaratish
        PassportData.objects.update_or_create(
            pinfl=PNFL,
            defaults={
                'passport_series': passport_data.get('ps_ser', ''),
                'passport_number': str(passport_data.get('ps_num', '')),
                'first_name': passport_data.get('fname', ''),
                'last_name': passport_data.get('sname', ''),
                'middle_name': passport_data.get('mname', ''),
                'birth_date': passport_data.get('birth_date', ''),
                'photo_base64': passport_data.get('photo', ''),
                'address': passport_data.get('birth_place', ''),
                'issued_by': passport_data.get('doc_give_place', ''),
                'issue_date': passport_data.get('matches_date_begin_document', ''),
                'expire_date': passport_data.get('matches_date_end_document', '')
            }
        )
        print(f"✅ PassportData created/updated")

        print("\n" + "="*60)
        print("✅ ADMIN USER SUCCESSFULLY CREATED!")
        print("="*60)
        print(f"Full Name: {passport_data.get('sname')} {passport_data.get('fname')} {passport_data.get('mname')}")
        print(f"Birth Date: {passport_data.get('birth_date')}")
        print(f"Username: {USERNAME}")
        print(f"Password: {PASSWORD}")
        print(f"PNFL: {PNFL}")
        print(f"Passport: {PASSPORT}")
        print(f"Role: ADMIN (Full access)")
        print("="*60)
        print("\n📝 Login instructions:")
        print("1. Go to: http://localhost:3030/login")
        print(f"2. Enter PNFL: {PNFL}")
        print(f"3. Enter Passport: {PASSPORT}")
        print("4. Look at camera for face authentication")
        print("\n✅ Real government passport photo will be used for face matching!")

    else:
        print(f"❌ Government API error: {data.get('message', 'Unknown error')}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
