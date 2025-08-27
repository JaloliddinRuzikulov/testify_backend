"""
Tashqi passport ma'lumotlar bazasidan ma'lumot olish xizmati
Bu modul haqiqiy passport bazasiga ulanish uchun ishlatiladi
"""

import base64
import requests
import json
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from .passport_models import PassportData

logger = logging.getLogger(__name__)


class PassportAPIService:
    """Tashqi passport API bilan ishlash xizmati"""
    
    # API configuration (settings.py da sozlanadi)
    API_BASE_URL = getattr(settings, 'PASSPORT_API_BASE_URL', 'https://passport.gov.uz/api/v1')
    API_KEY = getattr(settings, 'PASSPORT_API_KEY', '')
    API_SECRET = getattr(settings, 'PASSPORT_API_SECRET', '')
    
    # Cache configuration
    CACHE_TIMEOUT = 3600  # 1 soat
    CACHE_PREFIX = 'passport_api'
    
    def __init__(self):
        """Service initialization"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        if self.API_KEY:
            self.session.headers['X-API-Key'] = self.API_KEY
            
        if self.API_SECRET:
            self.session.headers['X-API-Secret'] = self.API_SECRET
    
    def get_passport_by_pinfl(self, pinfl: str) -> Optional[Dict[str, Any]]:
        """
        PINFL orqali passport ma'lumotlarini olish
        
        Args:
            pinfl: 14 xonali PINFL/JSHSHIR raqami
            
        Returns:
            Passport ma'lumotlari dict yoki None
        """
        try:
            # Cache'dan tekshirish
            cache_key = f"{self.CACHE_PREFIX}:pinfl:{pinfl}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Passport data for PINFL {pinfl} found in cache")
                return cached_data
            
            # API'ga so'rov yuborish
            response = self._make_api_request('GET', f'/passport/by-pinfl/{pinfl}')
            
            if response and response.get('success'):
                passport_data = response.get('data')
                
                # Cache'ga saqlash
                cache.set(cache_key, passport_data, self.CACHE_TIMEOUT)
                
                return passport_data
            
            logger.warning(f"No passport data found for PINFL: {pinfl}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching passport by PINFL {pinfl}: {str(e)}")
            return None
    
    def get_passport_by_series_number(self, series: str, number: str) -> Optional[Dict[str, Any]]:
        """
        Passport seriya va raqami orqali ma'lumot olish
        
        Args:
            series: Passport seriyasi (masalan: AA, AB)
            number: Passport raqami (masalan: 1234567)
            
        Returns:
            Passport ma'lumotlari dict yoki None
        """
        try:
            # Cache'dan tekshirish
            cache_key = f"{self.CACHE_PREFIX}:passport:{series}{number}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Passport data for {series}{number} found in cache")
                return cached_data
            
            # API'ga so'rov
            params = {
                'series': series.upper(),
                'number': number
            }
            response = self._make_api_request('GET', '/passport/by-document', params=params)
            
            if response and response.get('success'):
                passport_data = response.get('data')
                
                # Cache'ga saqlash
                cache.set(cache_key, passport_data, self.CACHE_TIMEOUT)
                
                return passport_data
            
            logger.warning(f"No passport data found for {series}{number}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching passport {series}{number}: {str(e)}")
            return None
    
    def verify_passport_data(self, pinfl: str, series: str, number: str, 
                            birth_date: str = None) -> Dict[str, Any]:
        """
        Passport ma'lumotlarini tekshirish
        
        Args:
            pinfl: PINFL raqami
            series: Passport seriyasi
            number: Passport raqami
            birth_date: Tug'ilgan sana (YYYY-MM-DD formatida)
            
        Returns:
            Tekshirish natijasi
        """
        result = {
            'valid': False,
            'message': '',
            'data': None
        }
        
        try:
            # API'ga tekshirish so'rovi
            payload = {
                'pinfl': pinfl,
                'passport_series': series.upper(),
                'passport_number': number
            }
            
            if birth_date:
                payload['birth_date'] = birth_date
            
            response = self._make_api_request('POST', '/passport/verify', json=payload)
            
            if response and response.get('success'):
                result['valid'] = response.get('valid', False)
                result['message'] = response.get('message', 'Tekshirish muvaffaqiyatli')
                result['data'] = response.get('data')
            else:
                result['message'] = response.get('message', 'Tekshirishda xatolik')
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying passport data: {str(e)}")
            result['message'] = f'Tekshirishda xatolik: {str(e)}'
            return result
    
    def sync_passport_to_database(self, passport_api_data: Dict[str, Any]) -> Optional[PassportData]:
        """
        API'dan olingan ma'lumotlarni local bazaga saqlash
        
        Args:
            passport_api_data: API'dan olingan passport ma'lumotlari
            
        Returns:
            PassportData modeli yoki None
        """
        try:
            # Ma'lumotlarni tayyorlash
            passport_data = {
                'passport_series': passport_api_data.get('series', ''),
                'passport_number': passport_api_data.get('number', ''),
                'pinfl': passport_api_data.get('pinfl', ''),
                'first_name': passport_api_data.get('first_name', ''),
                'last_name': passport_api_data.get('last_name', ''),
                'middle_name': passport_api_data.get('middle_name', ''),
                'birth_date': self._parse_date(passport_api_data.get('birth_date')),
                'photo_base64': passport_api_data.get('photo_base64', ''),
                'address': passport_api_data.get('address', ''),
                'issued_by': passport_api_data.get('issued_by', ''),
                'issue_date': self._parse_date(passport_api_data.get('issue_date')),
                'expire_date': self._parse_date(passport_api_data.get('expire_date')),
            }
            
            # Bazaga saqlash yoki yangilash
            passport_obj, created = PassportData.objects.update_or_create(
                pinfl=passport_data['pinfl'],
                defaults=passport_data
            )
            
            if created:
                logger.info(f"New passport data created for PINFL: {passport_data['pinfl']}")
            else:
                logger.info(f"Passport data updated for PINFL: {passport_data['pinfl']}")
            
            return passport_obj
            
        except Exception as e:
            logger.error(f"Error syncing passport data to database: {str(e)}")
            return None
    
    def fetch_and_sync_passport(self, pinfl: str = None, series: str = None, 
                               number: str = None) -> Optional[PassportData]:
        """
        API'dan passport ma'lumotlarini olib, bazaga saqlash
        
        Args:
            pinfl: PINFL raqami
            series: Passport seriyasi
            number: Passport raqami
            
        Returns:
            PassportData modeli yoki None
        """
        try:
            # Avval local bazadan qidirish
            if pinfl:
                try:
                    existing = PassportData.objects.get(pinfl=pinfl)
                    # Agar 24 soatdan kam bo'lsa, mavjudini qaytarish
                    if existing.updated_at > datetime.now() - timedelta(days=1):
                        return existing
                except PassportData.DoesNotExist:
                    pass
            
            # API'dan olish
            if pinfl:
                api_data = self.get_passport_by_pinfl(pinfl)
            elif series and number:
                api_data = self.get_passport_by_series_number(series, number)
            else:
                logger.error("Either PINFL or series+number required")
                return None
            
            if api_data:
                # Bazaga saqlash
                return self.sync_passport_to_database(api_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching and syncing passport: {str(e)}")
            return None
    
    def _make_api_request(self, method: str, endpoint: str, 
                         params: Dict = None, json: Dict = None) -> Optional[Dict]:
        """
        API'ga so'rov yuborish
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parametrlari
            json: Request body
            
        Returns:
            Response data yoki None
        """
        try:
            url = f"{self.API_BASE_URL}{endpoint}"
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=30
            )
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Sana stringini datetime.date obyektiga aylantirish
        
        Args:
            date_str: Sana string formatida
            
        Returns:
            datetime.date yoki None
        """
        if not date_str:
            return None
        
        try:
            # Turli formatlarni sinab ko'rish
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            return None


class MockPassportAPIService(PassportAPIService):
    """
    Test uchun mock passport API service
    Haqiqiy API mavjud bo'lmaganda ishlatiladi
    """
    
    def get_passport_by_pinfl(self, pinfl: str) -> Optional[Dict[str, Any]]:
        """Mock data qaytarish"""
        
        # Test ma'lumotlari
        mock_data = {
            '12345678901234': {
                'series': 'AA',
                'number': '1234567',
                'pinfl': '12345678901234',
                'first_name': 'Test',
                'last_name': 'User',
                'middle_name': 'Admin',
                'birth_date': '1990-01-01',
                'photo_base64': self._generate_mock_photo(),
                'address': 'Toshkent shahar, Yunusobod tumani',
                'issued_by': "O'zbekiston Respublikasi IIB",
                'issue_date': '2020-01-01',
                'expire_date': '2030-01-01'
            },
            '23456789012345': {
                'series': 'AB',
                'number': '2345678',
                'pinfl': '23456789012345',
                'first_name': 'Creator',
                'last_name': 'Test',
                'middle_name': 'User',
                'birth_date': '1995-05-15',
                'photo_base64': self._generate_mock_photo(),
                'address': 'Samarqand viloyati, Samarqand shahar',
                'issued_by': "O'zbekiston Respublikasi IIB",
                'issue_date': '2021-03-15',
                'expire_date': '2031-03-15'
            }
        }
        
        return mock_data.get(pinfl)
    
    def _generate_mock_photo(self) -> str:
        """Mock passport rasmi yaratish"""
        # 1x1 transparent PNG for testing
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def get_passport_service() -> PassportAPIService:
    """
    Passport service instance olish
    Settings'ga qarab haqiqiy yoki mock service qaytaradi
    """
    use_mock = getattr(settings, 'USE_MOCK_PASSPORT_API', True)
    
    if use_mock:
        return MockPassportAPIService()
    else:
        return PassportAPIService()