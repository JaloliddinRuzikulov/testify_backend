from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.utils import timezone
import logging

from .models import User
from .passport_models import PassportData, UserPassportLink
from .face_auth_service import FaceAuthenticationService
from .passport_api_service import get_passport_service
from .liveness_service import LivenessVerificationService
from .serializers import UserSerializer
from .permissions import IsAdmin

logger = logging.getLogger(__name__)


class FaceAuthRegisterView(APIView):
    """PINFL va yuz rasmi orqali ro'yxatdan o'tish - FAQAT ADMIN"""
    permission_classes = [IsAdmin]  # Faqat admin qila oladi
    
    def post(self, request):
        """
        PINFL va yuz rasmi orqali yangi foydalanuvchi yaratish
        
        Request body:
        {
            "pinfl": "12345678901234",
            "face_image": "data:image/jpeg;base64,..."
        }
        """
        pinfl = request.data.get('pinfl')
        face_image = request.data.get('face_image')
        
        if not pinfl or not face_image:
            return Response({
                'success': False,
                'message': _('PINFL va yuz rasmi majburiy')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Face authentication service
        face_service = FaceAuthenticationService()
        
        try:
            with transaction.atomic():
                # Ro'yxatdan o'tkazish
                result = face_service.register_user_with_passport(pinfl, face_image)
                
                if not result['success']:
                    return Response({
                        'success': False,
                        'message': result['message'],
                        'match_score': result.get('match_score', 0)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user = result['user']
                
                # JWT tokenlarni yaratish
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'message': result['message'],
                    'match_score': result['match_score'],
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token)
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Face registration error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Ro\'yxatdan o\'tishda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceAuthLoginView(APIView):
    """Yuz rasmi orqali login qilish"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Username/PINFL va yuz rasmi orqali login
        
        Request body:
        {
            "username": "AA1234567" yoki "pinfl": "12345678901234",
            "face_image": "data:image/jpeg;base64,..."
        }
        """
        username = request.data.get('username')
        pinfl = request.data.get('pinfl')
        face_image = request.data.get('face_image')
        liveness_data = request.data.get('liveness_data', None)
        
        if not face_image:
            return Response({
                'success': False,
                'message': _('Yuz rasmi majburiy')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not username and not pinfl:
            return Response({
                'success': False,
                'message': _('Username yoki PINFL majburiy')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Foydalanuvchini topish
            if username:
                user = User.objects.get(username=username)
            else:
                # PINFL orqali qidirish
                passport_link = UserPassportLink.objects.select_related('user').get(
                    passport_data__pinfl=pinfl
                )
                user = passport_link.user
            
            # Liveness verification first
            user_identifier = username or pinfl
            is_live, liveness_reason = LivenessVerificationService.verify_liveness(
                face_image, user_identifier, liveness_data
            )
            
            if not is_live:
                logger.warning(f"Liveness check failed for {user_identifier}: {liveness_reason}")
                return Response({
                    'success': False,
                    'message': f'Tiriklik tekshiruvi muvaffaqiyatsiz: {liveness_reason}',
                    'liveness_failed': True
                }, status=status.HTTP_403_FORBIDDEN)
            
            # IP va User-Agent olish
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Face authentication
            face_service = FaceAuthenticationService()
            result = face_service.verify_user_face(
                user, face_image, ip_address, user_agent
            )
            
            if not result['success']:
                # Shubhali faoliyatni tekshirish
                if face_service.check_suspicious_activity(user):
                    return Response({
                        'success': False,
                        'message': _('Ko\'p marta muvaffaqiyatsiz urinish. Account vaqtincha bloklangan'),
                        'blocked': True
                    }, status=status.HTTP_403_FORBIDDEN)
                
                return Response({
                    'success': False,
                    'message': result['message'],
                    'match_score': result.get('match_score', 0)
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # JWT tokenlarni yaratish
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': result['message'],
                'match_score': result['match_score'],
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': _('Foydalanuvchi topilmadi')
            }, status=status.HTTP_404_NOT_FOUND)
        except UserPassportLink.DoesNotExist:
            return Response({
                'success': False,
                'message': _('PINFL bo\'yicha foydalanuvchi topilmadi')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Face login error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Login qilishda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_client_ip(self, request):
        """Client IP manzilini olish"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VerifyPassportView(APIView):
    """Passport ma'lumotlarini tekshirish"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Foydalanuvchi passport ma'lumotlarini tekshirish
        
        Request body:
        {
            "pinfl": "12345678901234",
            "passport_series": "AA",
            "passport_number": "1234567"
        }
        """
        pinfl = request.data.get('pinfl')
        passport_series = request.data.get('passport_series')
        passport_number = request.data.get('passport_number')
        
        if not all([pinfl, passport_series, passport_number]):
            return Response({
                'success': False,
                'message': _('Barcha maydonlar to\'ldirilishi kerak')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Passport ma'lumotlarini tekshirish
            passport_data = PassportData.objects.get(
                pinfl=pinfl,
                passport_series=passport_series,
                passport_number=passport_number
            )
            
            # Foydalanuvchi bilan bog'lash
            user_passport, created = UserPassportLink.objects.get_or_create(
                user=request.user,
                defaults={'passport_data': passport_data}
            )
            
            if not created and user_passport.passport_data != passport_data:
                return Response({
                    'success': False,
                    'message': _('Siz boshqa passport bilan bog\'langansiz')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': _('Passport ma\'lumotlari tasdiqlandi'),
                'passport': {
                    'full_name': f"{passport_data.first_name} {passport_data.last_name}",
                    'birth_date': passport_data.birth_date,
                    'passport': f"{passport_data.passport_series}{passport_data.passport_number}",
                    'verified': user_passport.verified
                }
            }, status=status.HTTP_200_OK)
            
        except PassportData.DoesNotExist:
            return Response({
                'success': False,
                'message': _('Passport ma\'lumotlari topilmadi')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Passport verification error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Tekshirishda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceAuthHistoryView(APIView):
    """Face authentication tarixi"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Foydalanuvchi face auth tarixini olish"""
        face_service = FaceAuthenticationService()
        history = face_service.get_user_auth_history(request.user, limit=20)
        
        history_data = [{
            'status': log.status,
            'match_score': log.match_score,
            'attempted_at': log.attempted_at,
            'ip_address': log.ip_address,
            'error_message': log.error_message
        } for log in history]
        
        return Response({
            'success': True,
            'history': history_data
        }, status=status.HTTP_200_OK)


class UpdateFaceDescriptorView(APIView):
    """Yuz descriptorini yangilash"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Foydalanuvchi yuz descriptorini yangilash
        
        Request body:
        {
            "face_image": "data:image/jpeg;base64,..."
        }
        """
        face_image = request.data.get('face_image')
        
        if not face_image:
            return Response({
                'success': False,
                'message': _('Yuz rasmi majburiy')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Passport linkni tekshirish
            user_passport = UserPassportLink.objects.select_related('passport_data').get(
                user=request.user
            )
            
            # Yuz rasmini tekshirish va yangilash
            face_service = FaceAuthenticationService()
            
            # Yangi rasmdan encoding chiqarish
            input_image = face_service.base64_to_image(face_image)
            new_encoding = face_service.extract_face_encoding(input_image)
            
            if new_encoding is None:
                return Response({
                    'success': False,
                    'message': _('Rasmda yuz topilmadi')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Passport rasmi bilan solishtirish
            passport_image = face_service.base64_to_image(user_passport.passport_data.photo_base64)
            passport_encoding = face_service.extract_face_encoding(passport_image)
            
            if passport_encoding is None:
                return Response({
                    'success': False,
                    'message': _('Passport rasmida yuz topilmadi')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            match_score = face_service.compare_faces(passport_encoding, new_encoding)
            
            if match_score < face_service.MIN_MATCH_THRESHOLD:
                return Response({
                    'success': False,
                    'message': _('Yangi rasm passport rasmi bilan mos kelmadi'),
                    'match_score': match_score
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Descriptorni yangilash
            user_passport.passport_data.face_descriptors = new_encoding.tolist()
            user_passport.passport_data.save()
            
            # Match score yangilash
            user_passport.face_match_score = match_score
            if match_score >= face_service.HIGH_MATCH_THRESHOLD:
                user_passport.verified = True
                user_passport.verified_at = timezone.now()
            user_passport.save()
            
            return Response({
                'success': True,
                'message': _('Yuz ma\'lumotlari yangilandi'),
                'match_score': match_score
            }, status=status.HTTP_200_OK)
            
        except UserPassportLink.DoesNotExist:
            return Response({
                'success': False,
                'message': _('Passport ma\'lumotlari topilmadi')
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Face descriptor update error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Yangilashda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FetchPassportDataView(APIView):
    """Tashqi API'dan passport ma'lumotlarini olish"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        PINFL orqali passport ma'lumotlarini olish va bazaga saqlash
        
        Request body:
        {
            "pinfl": "12345678901234"
        }
        yoki
        {
            "passport_series": "AA",
            "passport_number": "1234567"
        }
        """
        pinfl = request.data.get('pinfl')
        passport_series = request.data.get('passport_series')
        passport_number = request.data.get('passport_number')
        
        if not pinfl and not (passport_series and passport_number):
            return Response({
                'success': False,
                'message': _('PINFL yoki passport ma\'lumotlari kerak')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Passport service orqali ma'lumot olish
            passport_service = get_passport_service()
            
            # API'dan olish va bazaga saqlash
            passport_data = passport_service.fetch_and_sync_passport(
                pinfl=pinfl,
                series=passport_series,
                number=passport_number
            )
            
            if passport_data:
                return Response({
                    'success': True,
                    'message': _('Passport ma\'lumotlari muvaffaqiyatli olindi'),
                    'data': {
                        'pinfl': passport_data.pinfl,
                        'passport': f"{passport_data.passport_series}{passport_data.passport_number}",
                        'full_name': f"{passport_data.first_name} {passport_data.last_name}",
                        'birth_date': passport_data.birth_date,
                        'has_photo': bool(passport_data.photo_base64)
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': _('Passport ma\'lumotlari topilmadi')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error fetching passport data: {str(e)}")
            return Response({
                'success': False,
                'message': _('Ma\'lumot olishda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnhancedFaceAuthRegisterView(APIView):
    """Kengaytirilgan ro'yxatdan o'tish - tashqi API bilan - FAQAT ADMIN"""
    permission_classes = [IsAdmin]  # Faqat admin qila oladi
    
    def post(self, request):
        """
        PINFL va yuz rasmi orqali ro'yxatdan o'tish
        Avval tashqi API'dan passport ma'lumotlarini oladi
        
        Request body:
        {
            "pinfl": "12345678901234",
            "face_image": "data:image/jpeg;base64,..."
        }
        """
        pinfl = request.data.get('pinfl')
        face_image = request.data.get('face_image')
        
        if not pinfl or not face_image:
            return Response({
                'success': False,
                'message': _('PINFL va yuz rasmi majburiy')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # 1. Tashqi API'dan passport ma'lumotlarini olish
                passport_service = get_passport_service()
                passport_data = passport_service.fetch_and_sync_passport(pinfl=pinfl)
                
                if not passport_data:
                    return Response({
                        'success': False,
                        'message': _('PINFL bo\'yicha passport ma\'lumotlari topilmadi')
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 2. Face authentication service orqali ro'yxatdan o'tkazish
                face_service = FaceAuthenticationService()
                result = face_service.register_user_with_passport(pinfl, face_image)
                
                if not result['success']:
                    return Response({
                        'success': False,
                        'message': result['message'],
                        'match_score': result.get('match_score', 0)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user = result['user']
                
                # JWT tokenlarni yaratish
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'message': result['message'],
                    'match_score': result['match_score'],
                    'user': UserSerializer(user).data,
                    'passport_info': {
                        'full_name': f"{passport_data.first_name} {passport_data.last_name}",
                        'passport': f"{passport_data.passport_series}{passport_data.passport_number}",
                        'birth_date': passport_data.birth_date
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token)
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Enhanced face registration error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Ro\'yxatdan o\'tishda xatolik yuz berdi')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)