"""
Government Passport Verification API Views
Davlat passport xizmati bilan integratsiya
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
# from django.utils.translation import gettext as _
# Translation causes issues, using plain strings instead
# _ = lambda x: x  # REMOVED - causes errors
from django.db import transaction
from django.utils import timezone
from datetime import datetime
import logging
import json

from .models import User
from .passport_models import UserProfile, PassportData, UserPassportLink, FaceAuthenticationLog
from .government_passport_service import get_government_passport_service
from .face_auth_service import FaceAuthenticationService
from .serializers import UserSerializer
from .permissions import IsAdmin

logger = logging.getLogger(__name__)


class CheckPersonalizationView(APIView):
    """
    PNFL va passport orqali fuqaro ma'lumotlarini tekshirish
    Government API orqali real ma'lumot olish
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Check passport data from government API
        
        Request:
        {
            "pnfl": "12345678901234",
            "passport": "AA1234567"
        }
        
        Response:
        {
            "status": 1,
            "message": "Success",
            "data": {...passport data...}
        }
        """
        pnfl = request.data.get('pnfl')
        passport = request.data.get('passport')
        
        # Convert to string and remove any non-digit characters for PNFL
        if pnfl:
            pnfl = str(pnfl).strip()
        
        logger.info(f"CheckPersonalization request - PNFL: {pnfl}, type: {type(pnfl)}, len: {len(pnfl) if pnfl else 0}")
        logger.info(f"CheckPersonalization request - Passport: {passport}")
        
        # Validation - check string length directly
        if not pnfl or len(pnfl) != 14 or not pnfl.isdigit():
            logger.error(f"PNFL validation failed - value: '{pnfl}', len: {len(pnfl) if pnfl else 0}, isdigit: {pnfl.isdigit() if pnfl else False}")
            return Response({
                'status': 0,
                'message': 'PNFL 14 ta raqamdan iborat bo\'lishi kerak'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not passport or len(passport) < 9:
            return Response({
                'status': 0,
                'message': 'Passport raqami noto\'g\'ri formatda'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Government API'ga so'rov
            service = get_government_passport_service()
            result = service.get_passport_data(str(pnfl), passport)
            
            if result.get('status') == 1:
                # Ma'lumotlarni bazaga saqlash
                passport_data = result.get('data', {})
                
                # UserProfile yaratish yoki yangilash
                profile, created = UserProfile.objects.update_or_create(
                    pnfl=int(pnfl),
                    defaults={
                        'ps_ser': passport_data.get('ps_ser', ''),
                        'ps_num': passport_data.get('ps_num', ''),
                        'sname': passport_data.get('sname', ''),
                        'fname': passport_data.get('fname', ''),
                        'mname': passport_data.get('mname', ''),
                        'birth_place': passport_data.get('birth_place', ''),
                        'birth_date': passport_data.get('birth_date'),
                        'birth_country': passport_data.get('birth_country', ''),
                        'birth_country_id': passport_data.get('birth_country_id', 0),
                        'livestatus': passport_data.get('livestatus', '0'),
                        'nationality': passport_data.get('nationality', ''),
                        'nationality_id': passport_data.get('nationality_id', 0),
                        'sex': passport_data.get('sex', '1'),
                        'doc_give_place': passport_data.get('doc_give_place', ''),
                        'doc_give_place_id': passport_data.get('doc_give_place_id', 0),
                        'matches_date_begin_document': passport_data.get('matches_date_begin_document'),
                        'matches_date_end_document': passport_data.get('matches_date_end_document'),
                        'photo': passport_data.get('photo', ''),
                        'is_verified': True,
                        'verified_at': timezone.now()
                    }
                )
                
                # Document validity check
                validity = service.get_document_validity(passport_data)
                
                # Response - DO NOT return sensitive passport data!
                return Response({
                    'status': 1,
                    'message': 'Ma\'lumotlar muvaffaqiyatli tekshirildi',
                    'data': {
                        'full_name': service.format_full_name(passport_data),
                        'has_photo': bool(passport_data.get('photo')),
                        'is_alive': service.is_person_alive(passport_data),
                        'doc_validity': validity,
                        'profile_created': created
                    }
                }, status=status.HTTP_200_OK)
                
            else:
                return Response({
                    'status': 0,
                    'message': result.get('message', 'Ma\'lumot topilmadi')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Personalization check error: {str(e)}")
            return Response({
                'status': 0,
                'message': 'Texnik xatolik yuz berdi'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GovernmentFaceLoginView(APIView):
    """
    Government passport + Face authentication login
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Login with PNFL and face image
        First checks user exists, then face matching
        
        Request:
        {
            "pnfl": "12345678901234",
            "face_image": "data:image/jpeg;base64,...",
            "liveness_data": {...} // Optional passive liveness data
        }
        """
        pnfl = request.data.get('pnfl')
        face_image = request.data.get('face_image')
        liveness_data = request.data.get('liveness_data', {})
        
        logger.info(f"Face login request received - PNFL: {pnfl[:6]}..." if pnfl else "No PNFL")
        
        # Passive liveness verification
        if liveness_data:
            logger.info(f"Passive liveness data received: confidence={liveness_data.get('confidence', 0):.2f}")
            
            # Check passive liveness indicators
            is_passive = liveness_data.get('passive', False)
            confidence = liveness_data.get('confidence', 0)
            
            if is_passive:
                # Validate passive liveness metrics
                micro_movements = liveness_data.get('microMovements', 0)
                lighting_variations = liveness_data.get('lightingVariations', 0)
                
                # Minimum threshold for passive liveness
                min_confidence = 0.4  # Lower threshold for passive detection
                
                if confidence < min_confidence and micro_movements < 5 and lighting_variations < 2:
                    logger.warning(f"Passive liveness verification failed: confidence={confidence:.2f}")
                    return Response({
                        'success': False,
                        'message': 'Kameraga to\'g\'ri qarang va tabiiy harakat qiling'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    logger.info(f"Passive liveness verified: movements={micro_movements}, variations={lighting_variations}")
        
        # Frontend rasmni tahlil qilish
        if face_image:
            import base64
            from PIL import Image
            from io import BytesIO
            
            try:
                if ',' in face_image:
                    prefix, b64_content = face_image.split(',', 1)
                    image_bytes = base64.b64decode(b64_content)
                else:
                    image_bytes = base64.b64decode(face_image)
                
                img = Image.open(BytesIO(image_bytes))
                logger.info(f"Frontend image: {img.size[0]}x{img.size[1]}, Format: {img.format}, Mode: {img.mode}")
            except Exception as e:
                logger.error(f"Frontend image analysis error: {e}")
        
        # Convert to string and validate
        if pnfl:
            pnfl = str(pnfl).strip()
        
        if not all([pnfl, face_image]):
            return Response({
                'success': False,
                'message': 'PNFL va yuz rasmi majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 1. Check if user exists with this PNFL
            try:
                user = User.objects.get(pnfl=pnfl)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Foydalanuvchi topilmadi. Admin orqali ro\'yxatdan o\'tkazilishi kerak.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 2. Get or create UserProfile if exists
            profile = None
            try:
                profile = UserProfile.objects.get(pnfl=int(pnfl))
            except UserProfile.DoesNotExist:
                # Profile doesn't exist yet, it's OK
                pass
            
            # 3. Face authentication
            face_service = FaceAuthenticationService()
            
            # PassportData'dan saqlangan rasmni olish - bu eng ishonchli manba
            passport_obj = None
            try:
                # Avval to'g'ridan-to'g'ri PNFL orqali PassportData'dan qidirish
                passport_obj = PassportData.objects.get(pinfl=str(pnfl))
                logger.info(f"PassportData topildi PNFL {pnfl} uchun")
            except PassportData.DoesNotExist:
                # Agar topilmasa, UserPassportLink orqali qidirish
                try:
                    user_passport = UserPassportLink.objects.get(user=user)
                    passport_obj = user_passport.passport_data
                    logger.info(f"PassportData UserPassportLink orqali topildi")
                except UserPassportLink.DoesNotExist:
                    logger.warning(f"PassportData topilmadi PNFL {pnfl} uchun")
                    pass
            
            # Saqlangan rasm yo'q bo'lsa, login qilish mumkin emas
            if not passport_obj or not passport_obj.photo_base64:
                logger.error(f"PassportData'da saqlangan rasm topilmadi PNFL {pnfl} uchun")
                return Response({
                    'success': False,
                    'message': 'Passport ma\'lumotlari topilmadi. Admin orqali ro\'yxatdan o\'tkazilishi kerak.',
                    'error': 'no_passport_photo'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # PassportData'dagi rasm bilan solishtirish
            logger.info(f"Yuz taqqoslash boshlanmoqda PNFL {pnfl} uchun")
            
            # face_service.verify_user_face o'rniga to'g'ridan-to'g'ri PassportData rasmini ishlatish
            face_service = FaceAuthenticationService()
            
            try:
                # PassportData'dagi saqlangan rasmni olish
                stored_face_image = passport_obj.photo_base64
                
                # Debug log
                logger.info(f"Stored image length: {len(stored_face_image) if stored_face_image else 0}")
                logger.info(f"Input image length: {len(face_image) if face_image else 0}")
                
                # Rasmlarni numpy array'ga aylantirish
                stored_image = face_service.base64_to_image(stored_face_image)
                input_image = face_service.base64_to_image(face_image)
                
                # Yuzlarni chiqarib olish va solishtirish
                stored_face = face_service.extract_face_encoding(stored_image)
                input_face = face_service.extract_face_encoding(input_image)
                
                if stored_face is None:
                    logger.error("PassportData rasmida yuz topilmadi")
                    return Response({
                        'success': False,
                        'message': 'Saqlangan passport rasmida yuz topilmadi',
                        'match_score': 0.0
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                if input_face is None:
                    logger.error("Kiritilgan rasmda yuz topilmadi")
                    return Response({
                        'success': False,
                        'message': 'Kiritilgan rasmda yuz topilmadi',
                        'match_score': 0.0
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Yuzlarni solishtirish
                match_score = face_service.compare_faces(stored_face, input_face)
                logger.info(f"Yuz taqqoslash natijasi: {match_score:.2%} moslik")
                
                # Log authentication attempt
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Yuz taqqoslash natijasi - XAVFSIZLIK MUHIM!
                threshold = 0.65  # 65% minimum threshold - yuqori xavfsizlik
                face_result = {
                    'success': match_score >= threshold,
                    'match_score': match_score,
                    'message': f'Yuz mos keldi ({match_score:.1%})' if match_score >= threshold else f'Yuz mos kelmadi ({match_score:.1%})'
                }
                
            except Exception as e:
                logger.error(f"Yuz taqqoslashda xatolik: {str(e)}")
                return Response({
                    'success': False,
                    'message': 'Yuz taqqoslashda texnik xatolik',
                    'match_score': 0.0
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if not face_result['success']:
                return Response({
                    'success': False,
                    'message': face_result['message'],
                    'match_score': face_result.get('match_score', 0)
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # JWT token yaratish
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Muvaffaqiyatli kirish',
                'match_score': face_result.get('match_score', 0),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name if not profile else profile.fname,
                    'last_name': user.last_name if not profile else profile.sname,
                    'role': user.role,
                    'pnfl': str(pnfl)
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                },
                'passport_info': {
                    'full_name': profile.full_name if profile else f"{user.first_name} {user.last_name}",
                    'birth_date': str(profile.birth_date) if profile else None,
                    'birth_place': profile.birth_place if profile else None,
                    'nationality': profile.nationality if profile else None,
                    'is_valid': profile.is_passport_valid if profile else True,
                    'expire_date': str(profile.matches_date_end_document) if profile else None
                } if profile else None
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Government face login error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Login jarayonida xatolik'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_client_ip(self, request):
        """Client IP manzilini olish"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class GetUserProfileView(APIView):
    """
    Foydalanuvchi to'liq profilini olish
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get current user's full profile with passport data
        """
        try:
            user = request.user
            
            # UserProfile mavjudligini tekshirish
            if hasattr(user, 'full_profile'):
                profile = user.full_profile
                
                return Response({
                    'success': True,
                    'data': {
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'role': user.role,
                            'is_active': user.is_active
                        },
                        'profile': {
                            'full_name': profile.full_name,
                            'passport': profile.passport,
                            'pnfl': str(profile.pnfl),
                            'birth_date': str(profile.birth_date),
                            'birth_place': profile.birth_place,
                            'age': profile.get_age(),
                            'sex': profile.get_sex_display(),
                            'nationality': profile.nationality,
                            'is_alive': profile.is_alive,
                            'is_passport_valid': profile.is_passport_valid,
                            'passport_expire_date': str(profile.matches_date_end_document),
                            'doc_give_place': profile.doc_give_place,
                            'has_photo': bool(profile.photo),
                            'is_verified': profile.is_verified
                        }
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Profil ma\'lumotlari topilmadi'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Get profile error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Profil olishda xatolik'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LinkUserToPassportView(APIView):
    """
    Admin uchun: Mavjud user'ni passport ma'lumotlari bilan bog'lash
    """
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """
        Link existing user to passport profile
        
        Request:
        {
            "user_id": 1,
            "pnfl": "12345678901234"
        }
        """
        user_id = request.data.get('user_id')
        pnfl = request.data.get('pnfl')
        
        if not user_id or not pnfl:
            return Response({
                'success': False,
                'message': 'User ID va PNFL majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # User tekshirish
                user = User.objects.get(id=user_id)
                
                # UserProfile tekshirish
                profile = UserProfile.objects.get(pnfl=int(pnfl))
                
                # Agar profile allaqachon boshqa userga bog'langan bo'lsa
                if profile.user and profile.user != user:
                    return Response({
                        'success': False,
                        'message': 'Bu passport boshqa foydalanuvchiga bog\'langan'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Bog'lash
                profile.user = user
                profile.save()
                
                # User ma'lumotlarini yangilash
                user.pnfl = profile.pnfl
                user.passport = profile.passport
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Foydalanuvchi passport bilan muvaffaqiyatli bog\'landi',
                    'data': {
                        'user_id': user.id,
                        'username': user.username,
                        'full_name': profile.full_name,
                        'passport': profile.passport,
                        'pnfl': str(profile.pnfl)
                    }
                }, status=status.HTTP_200_OK)
                
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Foydalanuvchi topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)
        except UserProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'PNFL bo\'yicha profil topilmadi. Avval passport tekshirish kerak.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Link user to passport error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Bog\'lashda xatolik'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)