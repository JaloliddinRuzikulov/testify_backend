"""
Government Passport API Service
O'zbekiston davlat passport ma'lumotlar bazasidan ma'lumot olish
Real API: http://imei_api.uzbmb.uz/compress
"""

import requests
import json
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)


class GovernmentPassportService:
    """
    O'zbekiston davlat passport xizmati bilan integratsiya
    UZBMB (O'zbekiston Milliy Banki) API orqali
    """
    
    # API endpoints
    BASE_URL = "http://imei_api.uzbmb.uz"
    PERSONALIZATION_ENDPOINT = "/compress"
    
    # Cache settings
    CACHE_TIMEOUT = 3600  # 1 soat
    CACHE_PREFIX = "gov_passport"
    
    def __init__(self):
        """Service initialization"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
    
    def get_passport_data(self, pnfl: str, passport: str) -> Dict[str, Any]:
        """
        PNFL va passport raqami orqali fuqaro ma'lumotlarini olish
        
        Args:
            pnfl: 14 xonali PINFL/JSHSHIR
            passport: Passport raqami (masalan: AA1234567)
            
        Returns:
            {
                'status': 1,  # 1 = success, 0 = error
                'data': {
                    'ps_ser': 'AA',
                    'ps_num': '1234567',
                    'pnfl': '12345678901234',
                    'sname': 'ABDULLAYEV',
                    'fname': 'ABDULLA',
                    'mname': 'ABDULLAYEVICH',
                    'birth_place': 'TOSHKENT SHAHAR',
                    'birth_date': '1990-01-01',
                    'birth_country': "O'ZBEKISTON",
                    'birth_country_id': 1,
                    'livestatus': '0',  # 0 = tirik, 1 = vafot etgan
                    'nationality': "O'ZBEK",
                    'nationality_id': 1,
                    'sex': '1',  # 1 = erkak, 2 = ayol
                    'doc_give_place': "YUNUSOBOD TUMANI IIB",
                    'doc_give_place_id': 10401,
                    'matches_date_begin_document': '2020-01-01',
                    'matches_date_end_document': '2030-01-01',
                    'photo': 'base64_encoded_photo_string'
                }
            }
        """
        try:
            # Cache'dan tekshirish
            cache_key = f"{self.CACHE_PREFIX}:{pnfl}:{passport}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Passport data for {pnfl} found in cache")
                return cached_data
            
            # API'ga so'rov
            url = f"{self.BASE_URL}{self.PERSONALIZATION_ENDPOINT}?imie={pnfl}&ps={passport}"
            
            logger.info(f"Requesting passport data from government API for PNFL: {pnfl}")
            logger.info(f"URL: {url}")
            
            response = self.session.get(
                url,
                verify=False,  # SSL verification o'chirilgan (government API uchun)
                timeout=10
            )
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                data = response.json()
                # If response is a string containing JSON, parse it again
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                        logger.info("Successfully parsed string response as JSON")
                    except json.JSONDecodeError:
                        logger.error(f"Government API returned non-JSON string: {data[:200]}")
                        return {
                            'status': 0,
                            'message': 'Davlat xizmatidan noto\'g\'ri javob keldi'
                        }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {response.text[:200]}")
                return {
                    'status': 0,
                    'message': 'Davlat xizmatidan noto\'g\'ri javob keldi'
                }
            
            # Cache'ga saqlash
            if isinstance(data, dict) and data.get('status') == 1:
                cache.set(cache_key, data, self.CACHE_TIMEOUT)
                logger.info(f"Successfully retrieved passport data for PNFL: {pnfl}")
            else:
                logger.warning(f"Government API returned error for PNFL: {pnfl}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching passport data for PNFL: {pnfl}")
            return {
                'status': 0,
                'message': 'Davlat xizmati javob bermadi (timeout)'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching passport data: {str(e)}")
            return {
                'status': 0,
                'message': f'Davlat xizmatiga ulanishda xatolik: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'status': 0,
                'message': 'Kutilmagan xatolik yuz berdi'
            }
    
    def verify_passport(self, pnfl: str, passport_series: str, passport_number: str) -> Dict[str, Any]:
        """
        Passport ma'lumotlarini tekshirish
        
        Args:
            pnfl: PINFL raqami
            passport_series: Passport seriyasi (AA, AB, ...)
            passport_number: Passport raqami (1234567)
            
        Returns:
            Verification result with passport data
        """
        passport = f"{passport_series}{passport_number}"
        return self.get_passport_data(pnfl, passport)
    
    def extract_passport_photo(self, passport_data: Dict[str, Any]) -> Optional[str]:
        """
        Passport ma'lumotlaridan foto chiqarish
        
        Args:
            passport_data: Government API'dan olingan ma'lumot
            
        Returns:
            Base64 encoded photo yoki None
        """
        try:
            if passport_data.get('status') == 1 and passport_data.get('data'):
                photo = passport_data['data'].get('photo')
                if photo:
                    # Agar photo data:image prefix'siz bo'lsa, qo'shamiz
                    if not photo.startswith('data:image'):
                        photo = f"data:image/jpeg;base64,{photo}"
                    return photo
        except Exception as e:
            logger.error(f"Error extracting photo: {str(e)}")
        
        return None
    
    def format_full_name(self, data: Dict[str, Any]) -> str:
        """
        To'liq ism shakllantrish
        
        Args:
            data: Passport ma'lumotlari
            
        Returns:
            Formatted full name
        """
        try:
            sname = data.get('sname', '').title()
            fname = data.get('fname', '').title()
            mname = data.get('mname', '').title()
            
            return f"{sname} {fname} {mname}".strip()
        except:
            return "Noma'lum"
    
    def get_gender_display(self, sex_code: str) -> str:
        """
        Jins kodini matn ko'rinishiga o'tkazish
        
        Args:
            sex_code: '1' yoki '2'
            
        Returns:
            'Erkak' yoki 'Ayol'
        """
        return "Erkak" if sex_code == "1" else "Ayol"
    
    def get_document_validity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Passport amal qilish muddatini tekshirish
        
        Args:
            data: Passport ma'lumotlari
            
        Returns:
            {
                'is_valid': bool,
                'days_remaining': int,
                'message': str
            }
        """
        try:
            end_date_str = data.get('matches_date_end_document')
            if not end_date_str:
                return {
                    'is_valid': False,
                    'days_remaining': 0,
                    'message': 'Amal qilish muddati aniqlanmadi'
                }
            
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            today = datetime.now()
            
            if end_date < today:
                return {
                    'is_valid': False,
                    'days_remaining': 0,
                    'message': 'Passport muddati tugagan'
                }
            
            days_remaining = (end_date - today).days
            
            if days_remaining < 30:
                message = f"Ogohlantirish: Passport {days_remaining} kundan keyin tugaydi"
            else:
                message = f"Passport amal qilish muddati: {end_date_str}"
            
            return {
                'is_valid': True,
                'days_remaining': days_remaining,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error checking document validity: {str(e)}")
            return {
                'is_valid': False,
                'days_remaining': 0,
                'message': 'Amal qilish muddatini tekshirishda xatolik'
            }
    
    def is_person_alive(self, data: Dict[str, Any]) -> bool:
        """
        Fuqaro tirikligini tekshirish
        
        Args:
            data: Passport ma'lumotlari
            
        Returns:
            True if alive, False otherwise
        """
        return data.get('livestatus', '0') == '0'


def get_government_passport_service() -> GovernmentPassportService:
    """
    Government passport service instance olish
    
    FAQAT REAL API ISHLATILADI - MOCK DATA YO'Q!
    """
    logger.info("Using REAL government passport service")
    return GovernmentPassportService()