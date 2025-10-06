#!/usr/bin/env python
"""
Admin user yaratish va government passport ma'lumotlari bilan bog'lash
Real test data: PNFL: 51304025740014, Passport: AC1987867
"""

import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import User
from users.passport_models import UserProfile, PassportData
from users.government_passport_service import get_government_passport_service

def create_admin_with_passport():
    """Real passport ma'lumotlari bilan admin user yaratish"""

    # Test ma'lumotlari
    PNFL = "51304025740014"
    PASSPORT = "AC1987867"
    USERNAME = "admin_ac1987867"
    PASSWORD = "Admin@2024!"

    print(f"Creating admin user with PNFL: {PNFL}, Passport: {PASSPORT}")

    try:
        # 1. Government API'dan passport ma'lumotlarini olish
        print("Fetching data from government API...")
        service = get_government_passport_service()
        result = service.get_passport_data(PNFL, PASSPORT)

        if result.get('status') != 1:
            print(f"❌ ERROR: Government API'dan ma'lumot olib bo'lmadi - {result.get('message')}")
            print(f"❌ Real PNFL va Passport kerak! Mock data ishlatilmaydi.")
            return  # Exit if no real data available
        else:
            passport_data = result.get('data', {})
            print(f"Successfully fetched passport data for: {passport_data.get('sname')} {passport_data.get('fname')}")

        # 2. User yaratish yoki yangilash
        user, user_created = User.objects.update_or_create(
            username=USERNAME,
            defaults={
                'email': f'{USERNAME}@dtm.uz',
                'first_name': passport_data.get('fname', 'Admin'),
                'last_name': passport_data.get('sname', 'User'),
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'pnfl': PNFL,
                'passport': PASSPORT
            }
        )

        if user_created:
            user.set_password(PASSWORD)
            user.save()
            print(f"✅ Admin user created: {USERNAME}")
        else:
            # Agar user mavjud bo'lsa, parolni yangilaymiz
            user.set_password(PASSWORD)
            user.role = User.Role.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.pnfl = PNFL
            user.passport = PASSPORT
            user.save()
            print(f"✅ Admin user updated: {USERNAME}")

        # 3. UserProfile yaratish yoki yangilash
        profile, profile_created = UserProfile.objects.update_or_create(
            pnfl=int(PNFL),
            defaults={
                'user': user,
                'ps_ser': passport_data.get('ps_ser', 'AC'),
                'ps_num': passport_data.get('ps_num', '1987867'),
                'sname': passport_data.get('sname', 'ADMINOV'),
                'fname': passport_data.get('fname', 'ADMIN'),
                'mname': passport_data.get('mname', 'ADMINOVICH'),
                'birth_place': passport_data.get('birth_place', 'TOSHKENT'),
                'birth_date': passport_data.get('birth_date', '1990-01-01'),
                'birth_country': passport_data.get('birth_country', "O'ZBEKISTON"),
                'birth_country_id': passport_data.get('birth_country_id', 1),
                'livestatus': passport_data.get('livestatus', '0'),
                'nationality': passport_data.get('nationality', "O'ZBEK"),
                'nationality_id': passport_data.get('nationality_id', 1),
                'sex': passport_data.get('sex', '1'),
                'doc_give_place': passport_data.get('doc_give_place', 'YUNUSOBOD IIB'),
                'doc_give_place_id': passport_data.get('doc_give_place_id', 10401),
                'matches_date_begin_document': passport_data.get('matches_date_begin_document', '2020-01-01'),
                'matches_date_end_document': passport_data.get('matches_date_end_document', '2030-01-01'),
                'photo': passport_data.get('photo', ''),
                'is_verified': True,
                'verified_at': timezone.now()
            }
        )

        if profile_created:
            print(f"✅ UserProfile created for PNFL: {PNFL}")
        else:
            print(f"✅ UserProfile updated for PNFL: {PNFL}")

        # 4. PassportData yaratish (agar kerak bo'lsa)
        passport_obj, passport_created = PassportData.objects.update_or_create(
            pinfl=PNFL,
            defaults={
                'passport_series': passport_data.get('ps_ser', 'AC'),
                'passport_number': passport_data.get('ps_num', '1987867'),
                'first_name': passport_data.get('fname', 'ADMIN'),
                'last_name': passport_data.get('sname', 'ADMINOV'),
                'middle_name': passport_data.get('mname', 'ADMINOVICH'),
                'birth_date': passport_data.get('birth_date', '1990-01-01'),
                'photo_base64': passport_data.get('photo', ''),
                'address': passport_data.get('birth_place', 'TOSHKENT'),
                'issued_by': passport_data.get('doc_give_place', 'YUNUSOBOD IIB'),
                'issue_date': passport_data.get('matches_date_begin_document', '2020-01-01'),
                'expire_date': passport_data.get('matches_date_end_document', '2030-01-01')
            }
        )

        if passport_created:
            print(f"✅ PassportData created")
        else:
            print(f"✅ PassportData updated")

        print("\n" + "="*60)
        print("✅ ADMIN USER SUCCESSFULLY CREATED!")
        print("="*60)
        print(f"Username: {USERNAME}")
        print(f"Password: {PASSWORD}")
        print(f"PNFL: {PNFL}")
        print(f"Passport: {PASSPORT}")
        print(f"Full Name: {profile.full_name}")
        print(f"Role: ADMIN (Full access)")
        print("="*60)
        print("\n📝 Login instructions:")
        print("1. Go to: http://localhost:3030/login")
        print(f"2. Enter PNFL: {PNFL}")
        print(f"3. Enter Passport: {PASSPORT}")
        print("4. Look at camera for face authentication")
        print("\n⚠️  Note: Face authentication will use government passport photo")

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_admin_with_passport()
