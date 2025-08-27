#!/usr/bin/env python
"""
Script to create a creator user with government passport data
"""
import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_platform.settings')
django.setup()

from users.government_passport_service import get_government_passport_service
from users.models import User
from users.passport_models import PassportData, UserProfile
from django.utils import timezone

def create_creator_user(pnfl, passport):
    """Create a creator user with government passport data"""
    
    # Government service'dan passport ma'lumotlarini olish
    service = get_government_passport_service()
    
    print(f'📋 Government API ga so\'rov yuborilmoqda...')
    print(f'   PNFL: {pnfl}')
    print(f'   Passport: {passport}')
    
    result = service.get_passport_data(pnfl, passport)
    
    if result.get('status') == 1:
        passport_info = result.get('data', {})
        print(f'✅ Passport ma\'lumotlari olindi:')
        print(f'   Ism: {passport_info.get("fname", "")}')
        print(f'   Familiya: {passport_info.get("sname", "")}')
        print(f'   Otasining ismi: {passport_info.get("mname", "")}')
        print(f'   Tug\'ilgan sana: {passport_info.get("birth_date", "")}')
        print(f'   Rasm mavjud: {"Ha" if passport_info.get("photo") else "Yo\'q"}')
        
        # PassportData yaratish yoki yangilash
        passport_data, created = PassportData.objects.update_or_create(
            pinfl=pnfl,
            defaults={
                'passport_series': passport_info.get('ps_ser', 'AC'),
                'passport_number': passport_info.get('ps_num', '2397533'),
                'first_name': passport_info.get('fname', ''),
                'last_name': passport_info.get('sname', ''),
                'middle_name': passport_info.get('mname', ''),
                'birth_date': passport_info.get('birth_date'),
                'photo_base64': passport_info.get('photo', ''),
                'created_at': timezone.now()
            }
        )
        print(f'✅ PassportData {"yaratildi" if created else "yangilandi"}')
        
        # UserProfile yaratish yoki yangilash
        profile, profile_created = UserProfile.objects.update_or_create(
            pnfl=int(pnfl),
            defaults={
                'ps_ser': passport_info.get('ps_ser', ''),
                'ps_num': passport_info.get('ps_num', ''),
                'sname': passport_info.get('sname', ''),
                'fname': passport_info.get('fname', ''),
                'mname': passport_info.get('mname', ''),
                'birth_place': passport_info.get('birth_place', ''),
                'birth_date': passport_info.get('birth_date'),
                'birth_country': passport_info.get('birth_country', ''),
                'birth_country_id': passport_info.get('birth_country_id', 0),
                'livestatus': passport_info.get('livestatus', '0'),
                'nationality': passport_info.get('nationality', ''),
                'nationality_id': passport_info.get('nationality_id', 0),
                'sex': passport_info.get('sex', '1'),
                'doc_give_place': passport_info.get('doc_give_place', ''),
                'doc_give_place_id': passport_info.get('doc_give_place_id', 0),
                'matches_date_begin_document': passport_info.get('matches_date_begin_document'),
                'matches_date_end_document': passport_info.get('matches_date_end_document'),
                'photo': passport_info.get('photo', ''),
                'is_verified': True,
                'verified_at': timezone.now()
            }
        )
        print(f'✅ UserProfile {"yaratildi" if profile_created else "yangilandi"}')
        
        # User yaratish yoki yangilash
        user, user_created = User.objects.update_or_create(
            username=passport,  # Passport raqami username sifatida
            defaults={
                'pnfl': pnfl,
                'first_name': passport_info.get('fname', ''),
                'last_name': passport_info.get('sname', ''),
                'role': 'CREATOR',
                'is_active': True
            }
        )
        
        if user_created:
            user.set_password(passport)  # Passport raqami parol sifatida
            user.save()
            print(f'✅ Creator user yaratildi:')
        else:
            print(f'ℹ️ User allaqachon mavjud, ma\'lumotlar yangilandi:')
        
        print(f'   Username: {user.username}')
        print(f'   Password: {passport}')
        print(f'   PNFL: {user.pnfl}')
        print(f'   To\'liq ism: {user.first_name} {user.last_name}')
        print(f'   Role: {user.role}')
        
        return True
        
    else:
        print(f'❌ Xatolik: {result.get("message", "Ma\'lumot topilmadi")}')
        return False

if __name__ == '__main__':
    # Parametrlar
    pnfl = '50109035550030'
    passport = 'AC2397533'
    
    # User yaratish
    success = create_creator_user(pnfl, passport)
    
    if success:
        print('\n✅ Barcha jarayonlar muvaffaqiyatli yakunlandi!')
    else:
        print('\n❌ User yaratishda xatolik!')
        sys.exit(1)