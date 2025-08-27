import base64
import numpy as np
import json
import requests
from typing import Optional, Dict, Any, List, Tuple
from django.conf import settings
from django.utils import timezone
from PIL import Image
from io import BytesIO
import logging

# OpenCV va face recognition kutubxonalarini import qilish
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    face_recognition = None

# DeepFace kutubxonasi - eng aniq yuz taqqoslash
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    DeepFace = None

# Scikit-image for real face comparison
try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.transform import resize
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

from .models import User
from .passport_models import PassportData, UserPassportLink, FaceAuthenticationLog, UserProfile

logger = logging.getLogger(__name__)


class FaceAuthenticationService:
    """Face authentication xizmati - passport rasmlardan foydalanib autentifikatsiya"""
    
    # Minimal moslik darajasi (0-1 oralig'ida)
    # XAVFSIZLIK MUHIM - yuqori aniqlik kerak!
    MIN_MATCH_THRESHOLD = 0.65  # 65% moslik - minimal xavfsizlik uchun
    HIGH_MATCH_THRESHOLD = 0.80  # 80% yuqori moslik
    
    def __init__(self):
        if CV2_AVAILABLE:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.orb = cv2.ORB_create()  # For feature matching
            logger.info("OpenCV face detection initialized")
        else:
            self.face_cascade = None
            self.orb = None
            logger.error("OpenCV not available - face authentication will not work!")
    
    def base64_to_image(self, base64_string: str) -> np.ndarray:
        """Base64 stringni OpenCV image arrayga aylantirish"""
        try:
            # Base64 prefiksni olib tashlash
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Base64 stringni tozalash
            import re
            # Remove all whitespace and newlines
            base64_string = ''.join(base64_string.split())
            
            # Remove ALL non-base64 characters including existing padding
            base64_string = re.sub(r'[^A-Za-z0-9+/]', '', base64_string)
            
            # Ensure the string length is divisible by 4
            # Truncate if necessary
            remainder = len(base64_string) % 4
            if remainder == 1:
                # This is invalid - truncate one character
                base64_string = base64_string[:-1]
            elif remainder == 2:
                # Need 2 padding chars
                base64_string += '=='
            elif remainder == 3:
                # Need 1 padding char
                base64_string += '='
            
            logger.info(f"Base64 string length after cleaning: {len(base64_string)}")
            
            # Decode base64 with better error handling
            try:
                image_bytes = base64.b64decode(base64_string)
            except Exception as decode_error:
                logger.error(f"Base64 decode error details: {str(decode_error)}")
                logger.error(f"String length: {len(base64_string)}, First 50 chars: {base64_string[:50]}")
                # Try alternative approach
                try:
                    # Add padding one more time
                    if len(base64_string) % 4:
                        base64_string += '=' * (4 - len(base64_string) % 4)
                    image_bytes = base64.b64decode(base64_string)
                except:
                    raise ValueError(f"Base64 decode failed: {str(decode_error)}")
            
            # PIL Image yaratish
            pil_image = Image.open(BytesIO(image_bytes))
            
            # RGB ga aylantirish (agar kerak bo'lsa)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # NumPy arrayga aylantirish
            image_array = np.array(pil_image)
            
            logger.info(f"Image successfully decoded: shape={image_array.shape}")
            return image_array
            
        except Exception as e:
            logger.error(f"Base64 to image conversion error: {str(e)}")
            raise ValueError(f"Rasmni o'qishda xatolik: {str(e)}")
    
    def extract_face_region(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Extract face region from image using OpenCV"""
        try:
            if not CV2_AVAILABLE:
                logger.error("OpenCV not available")
                return None
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            if len(faces) == 0:
                logger.warning("No face detected in image")
                return None
            
            # Get the largest face
            face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = face
            
            # Add more padding to match passport photo style
            padding_x = int(w * 0.3)
            padding_y = int(h * 0.4)
            x = max(0, x - padding_x)
            y = max(0, y - padding_y)
            w = min(image.shape[1] - x, w + 2 * padding_x)
            h = min(image.shape[0] - y, h + 2 * padding_y)
            
            # Extract and resize face region
            face_region = image[y:y+h, x:x+w]
            face_region = cv2.resize(face_region, (256, 256))
            
            return face_region
            
        except Exception as e:
            logger.error(f"Face extraction error: {str(e)}")
            return None
    
    def extract_face_encoding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Rasmdan yuz encodingini chiqarish"""
        try:
            if FACE_RECOGNITION_AVAILABLE:
                # Use face_recognition if available
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    logger.warning("No face detected with face_recognition")
                    return None
                
                # Get the largest face
                if len(face_locations) > 1:
                    face_locations = [max(face_locations, 
                                         key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))]
                
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                if face_encodings:
                    return face_encodings[0]
            else:
                # Use OpenCV face region as encoding
                face_region = self.extract_face_region(image)
                if face_region is not None:
                    return face_region  # Return face region as "encoding"
            
            return None
            
        except Exception as e:
            logger.error(f"Face encoding extraction error: {str(e)}")
            return None
    
    def compare_faces(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """Real face comparison using available methods"""
        try:
            # Avval DeepFace bilan urinib ko'ramiz - eng aniq usul
            if DEEPFACE_AVAILABLE and len(encoding1.shape) == 3 and len(encoding2.shape) == 3:
                try:
                    logger.info("DeepFace yuz taqqoslash boshlanmoqda...")
                    
                    # Vaqtinchalik fayllarni saqlash
                    import tempfile
                    import os
                    from PIL import Image
                    
                    # Rasmlarni vaqtinchalik fayllarga saqlash
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f1:
                        img1 = Image.fromarray(encoding1)
                        img1.save(f1.name, 'JPEG')
                        img1_path = f1.name
                    
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f2:
                        img2 = Image.fromarray(encoding2)
                        img2.save(f2.name, 'JPEG')
                        img2_path = f2.name
                    
                    # DeepFace bilan yuzlarni taqqoslash
                    # VGG-Face modeli eng aniq, lekin yuklanishi kerak
                    result = DeepFace.verify(
                        img1_path=img1_path,
                        img2_path=img2_path,
                        model_name='Facenet',  # Facenet yoki VGG-Face ishlatish mumkin
                        distance_metric='cosine',
                        enforce_detection=False  # Agar yuz topilmasa ham davom etsin
                    )
                    
                    # Vaqtinchalik fayllarni o'chirish
                    os.unlink(img1_path)
                    os.unlink(img2_path)
                    
                    # DeepFace natijasini olish
                    is_verified = result['verified']
                    distance = result['distance']
                    
                    # Distance ni similarity score ga aylantirish
                    # Cosine distance: 0 = bir xil, 2 = butunlay boshqa
                    similarity = max(0, 1 - (distance / 2))
                    
                    logger.info(f"DeepFace natijasi - Verified: {is_verified}, Distance: {distance:.3f}, Similarity: {similarity:.3f}")
                    
                    # Agar DeepFace yuqori ishonch bilan tasdiqlamasa, boshqa usullar bilan qo'shib hisoblash
                    if similarity < 0.7:
                        # Qo'shimcha tekshirish uchun boshqa usullar
                        if CV2_AVAILABLE and SKIMAGE_AVAILABLE:
                            gray1 = cv2.cvtColor(encoding1, cv2.COLOR_RGB2GRAY)
                            gray2 = cv2.cvtColor(encoding2, cv2.COLOR_RGB2GRAY)
                            
                            ssim_score = ssim(gray1, gray2)
                            hist_score = self._compare_histograms(encoding1, encoding2)
                            
                            # DeepFace natijasini asosiy qilib, boshqalarni qo'shimcha sifatida ishlatish
                            final_score = (similarity * 0.6 + ssim_score * 0.25 + hist_score * 0.15)
                            
                            logger.info(f"Aralash natija - DeepFace: {similarity:.3f}, SSIM: {ssim_score:.3f}, Hist: {hist_score:.3f}, Final: {final_score:.3f}")
                            
                            return final_score
                    
                    return similarity
                    
                except Exception as e:
                    logger.error(f"DeepFace taqqoslashda xatolik: {str(e)}")
                    # DeepFace ishlamasa, boshqa usullarga o'tish
                    pass
            
            # Agar DeepFace ishlamasa, mavjud usullardan foydalanish
            if FACE_RECOGNITION_AVAILABLE:
                # Use face_recognition library if available
                distance = face_recognition.face_distance([encoding1], encoding2)[0]
                
                # Convert distance to similarity score
                if distance > 1.0:
                    return 0.0
                else:
                    return 1.0 - distance
            
            elif CV2_AVAILABLE and SKIMAGE_AVAILABLE:
                # Use real image comparison with OpenCV and scikit-image
                logger.info("Using OpenCV/scikit-image for face comparison")
                
                # Ensure both are face regions (2D images)
                if len(encoding1.shape) == 3 and len(encoding2.shape) == 3:
                    # Convert to grayscale for comparison
                    gray1 = cv2.cvtColor(encoding1, cv2.COLOR_RGB2GRAY)
                    gray2 = cv2.cvtColor(encoding2, cv2.COLOR_RGB2GRAY)
                    
                    # Method 1: Structural Similarity Index (SSIM)
                    ssim_score = ssim(gray1, gray2)
                    
                    # Method 2: ORB feature matching
                    orb_score = self._compare_with_orb(gray1, gray2)
                    
                    # Method 3: Histogram comparison
                    hist_score = self._compare_histograms(encoding1, encoding2)
                    
                    # Weighted average of all methods - optimized weights
                    # SSIM va histogram ko'proq ishonchli
                    final_score = (ssim_score * 0.5 + orb_score * 0.2 + hist_score * 0.3)
                    
                    logger.info(f"Face comparison scores - SSIM: {ssim_score:.3f}, ORB: {orb_score:.3f}, Hist: {hist_score:.3f}, Final: {final_score:.3f}")
                    
                    return final_score
                else:
                    logger.error("Invalid encoding format for comparison")
                    return 0.0
            else:
                logger.error("No face comparison method available!")
                return 0.0
                
        except Exception as e:
            logger.error(f"Face comparison error: {str(e)}")
            return 0.0
    
    def _compare_with_orb(self, gray1: np.ndarray, gray2: np.ndarray) -> float:
        """Compare faces using ORB feature matching"""
        try:
            if not self.orb:
                return 0.0
            
            # Find keypoints and descriptors
            kp1, des1 = self.orb.detectAndCompute(gray1, None)
            kp2, des2 = self.orb.detectAndCompute(gray2, None)
            
            if des1 is None or des2 is None:
                return 0.0
            
            # Match features using BFMatcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            
            # Calculate similarity based on number of good matches
            max_matches = min(len(kp1), len(kp2))
            if max_matches == 0:
                return 0.0
            
            good_matches = [m for m in matches if m.distance < 50]
            score = len(good_matches) / max_matches
            
            return min(1.0, score * 2)  # Scale up the score
            
        except Exception as e:
            logger.error(f"ORB comparison error: {str(e)}")
            return 0.0
    
    def _compare_histograms(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compare color histograms of two face images"""
        try:
            # Calculate histograms for each channel
            hist1_r = cv2.calcHist([img1], [0], None, [256], [0, 256])
            hist1_g = cv2.calcHist([img1], [1], None, [256], [0, 256])
            hist1_b = cv2.calcHist([img1], [2], None, [256], [0, 256])
            
            hist2_r = cv2.calcHist([img2], [0], None, [256], [0, 256])
            hist2_g = cv2.calcHist([img2], [1], None, [256], [0, 256])
            hist2_b = cv2.calcHist([img2], [2], None, [256], [0, 256])
            
            # Normalize histograms
            hist1_r = cv2.normalize(hist1_r, hist1_r).flatten()
            hist1_g = cv2.normalize(hist1_g, hist1_g).flatten()
            hist1_b = cv2.normalize(hist1_b, hist1_b).flatten()
            
            hist2_r = cv2.normalize(hist2_r, hist2_r).flatten()
            hist2_g = cv2.normalize(hist2_g, hist2_g).flatten()
            hist2_b = cv2.normalize(hist2_b, hist2_b).flatten()
            
            # Compare using correlation
            score_r = cv2.compareHist(hist1_r, hist2_r, cv2.HISTCMP_CORREL)
            score_g = cv2.compareHist(hist1_g, hist2_g, cv2.HISTCMP_CORREL)
            score_b = cv2.compareHist(hist1_b, hist2_b, cv2.HISTCMP_CORREL)
            
            # Average of all channels
            score = (score_r + score_g + score_b) / 3.0
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Histogram comparison error: {str(e)}")
            return 0.0
    
    def verify_user_face(self, user: User, face_image_base64: str, 
                        ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Foydalanuvchi yuzini passport rasmi bilan solishtirish"""
        
        result = {
            'success': False,
            'message': '',
            'match_score': 0.0,
            'status': FaceAuthenticationLog.AuthStatus.FAILED
        }
        
        try:
            # User passport ma'lumotlarini olish
            # Avval UserProfile'dan government photo'ni olishga harakat qilamiz
            passport_photo = None
            
            # UserProfile'dan government API photo'sini olish
            try:
                user_profile = UserProfile.objects.get(user=user)
                if user_profile.photo:
                    passport_photo = user_profile.photo
                    logger.info(f"Using government API photo for user {user.username}")
            except UserProfile.DoesNotExist:
                logger.info(f"UserProfile not found for user {user.username}, checking PassportData")
            
            # Agar UserProfile'da yo'q bo'lsa, PassportData'dan olish
            if not passport_photo:
                try:
                    user_passport = UserPassportLink.objects.select_related('passport_data').get(user=user)
                    passport_data = user_passport.passport_data
                    passport_photo = passport_data.photo_base64
                except UserPassportLink.DoesNotExist:
                    # PassportData'dan to'g'ridan-to'g'ri olishga harakat
                    try:
                        passport_data = PassportData.objects.get(pinfl=user.pnfl)
                        passport_photo = passport_data.photo_base64
                    except:
                        pass
            
            if not passport_photo:
                result['message'] = 'Passport fotosi topilmadi'
                result['status'] = FaceAuthenticationLog.AuthStatus.FAILED
                self._log_authentication(user, result['status'], ip_address, user_agent, 
                                        error_message=result['message'])
                return result
            
            # Passport rasmidan yuz encodingini olish
            passport_image = self.base64_to_image(passport_photo)
            passport_encoding = self.extract_face_encoding(passport_image)
            
            if passport_encoding is None:
                result['message'] = 'Passport rasmida yuz topilmadi'
                result['status'] = FaceAuthenticationLog.AuthStatus.NO_FACE
                self._log_authentication(user, result['status'], ip_address, user_agent,
                                        error_message=result['message'])
                return result
            
            # Kiritilgan rasmdan yuz encodingini olish
            input_image = self.base64_to_image(face_image_base64)
            input_encoding = self.extract_face_encoding(input_image)
            
            if input_encoding is None:
                result['message'] = 'Kiritilgan rasmda yuz topilmadi'
                result['status'] = FaceAuthenticationLog.AuthStatus.NO_FACE
                self._log_authentication(user, result['status'], ip_address, user_agent,
                                        match_score=0.0, error_message=result['message'])
                return result
            
            # Yuzlarni solishtirish
            match_score = self.compare_faces(passport_encoding, input_encoding)
            result['match_score'] = match_score
            
            if match_score >= self.HIGH_MATCH_THRESHOLD:
                result['success'] = True
                result['message'] = 'Yuz muvaffaqiyatli tasdiqlandi'
                result['status'] = FaceAuthenticationLog.AuthStatus.SUCCESS
                    
            elif match_score >= self.MIN_MATCH_THRESHOLD:
                result['message'] = 'Yuz qisman mos keldi. Iltimos, yaxshi yoritilgan joyda qayta urinib ko\'ring'
                result['status'] = FaceAuthenticationLog.AuthStatus.LOW_QUALITY
            else:
                result['message'] = 'Yuz mos kelmadi'
                result['status'] = FaceAuthenticationLog.AuthStatus.FAILED
            
            # Autentifikatsiya logini saqlash
            self._log_authentication(user, result['status'], ip_address, user_agent,
                                    match_score=match_score, error_message=result.get('message', ''))
            
            return result
            
        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            result['message'] = f'Xatolik yuz berdi: {str(e)}'
            result['status'] = FaceAuthenticationLog.AuthStatus.FAILED
            self._log_authentication(user, result['status'], ip_address, user_agent,
                                    error_message=str(e))
            return result
    
    def register_user_with_passport(self, pinfl: str, face_image_base64: str) -> Dict[str, Any]:
        """PINFL va yuz rasmi orqali foydalanuvchini ro'yxatdan o'tkazish"""
        
        result = {
            'success': False,
            'message': '',
            'user': None,
            'match_score': 0.0
        }
        
        try:
            # Passport ma'lumotlarini PINFL orqali qidirish
            try:
                passport_data = PassportData.objects.get(pinfl=pinfl)
            except PassportData.DoesNotExist:
                result['message'] = 'PINFL bo\'yicha passport ma\'lumotlari topilmadi'
                return result
            
            # Yuzni passport rasmi bilan solishtirish
            passport_image = self.base64_to_image(passport_data.photo_base64)
            passport_encoding = self.extract_face_encoding(passport_image)
            
            if passport_encoding is None:
                result['message'] = 'Passport rasmida yuz topilmadi'
                return result
            
            input_image = self.base64_to_image(face_image_base64)
            input_encoding = self.extract_face_encoding(input_image)
            
            if input_encoding is None:
                result['message'] = 'Kiritilgan rasmda yuz topilmadi'
                return result
            
            match_score = self.compare_faces(passport_encoding, input_encoding)
            result['match_score'] = match_score
            
            if match_score < self.MIN_MATCH_THRESHOLD:
                result['message'] = 'Yuz passport rasmi bilan mos kelmadi'
                return result
            
            # Foydalanuvchi yaratish yoki yangilash
            username = f"{passport_data.passport_series}{passport_data.passport_number}"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': passport_data.first_name,
                    'last_name': passport_data.last_name,
                    'email': f"{username}@dtm.uz",  # Vaqtinchalik email
                    'role': User.Role.CREATOR  # Default rol
                }
            )
            
            if not created:
                # Mavjud foydalanuvchi ma'lumotlarini yangilash
                user.first_name = passport_data.first_name
                user.last_name = passport_data.last_name
                user.save()
            
            # User-Passport linkni yaratish yoki yangilash
            user_passport, link_created = UserPassportLink.objects.get_or_create(
                user=user,
                defaults={
                    'passport_data': passport_data,
                    'verified': match_score >= self.HIGH_MATCH_THRESHOLD,
                    'verified_at': timezone.now() if match_score >= self.HIGH_MATCH_THRESHOLD else None,
                    'face_match_score': match_score
                }
            )
            
            if not link_created:
                user_passport.face_match_score = match_score
                if match_score >= self.HIGH_MATCH_THRESHOLD:
                    user_passport.verified = True
                    user_passport.verified_at = timezone.now()
                user_passport.save()
            
            # Face descriptorni saqlash
            if passport_encoding is not None:
                passport_data.face_descriptors = passport_encoding.tolist()
                passport_data.save()
            
            result['success'] = True
            result['message'] = 'Ro\'yxatdan o\'tish muvaffaqiyatli'
            result['user'] = user
            
            return result
            
        except Exception as e:
            logger.error(f"User registration error: {str(e)}")
            result['message'] = f'Ro\'yxatdan o\'tishda xatolik: {str(e)}'
            return result
    
    def _log_authentication(self, user: User, status: str, ip_address: str = None,
                           user_agent: str = None, match_score: float = None,
                           error_message: str = ''):
        """Autentifikatsiya urinishini loglash"""
        try:
            FaceAuthenticationLog.objects.create(
                user=user,
                status=status,
                match_score=match_score,
                ip_address=ip_address or '0.0.0.0',
                user_agent=user_agent or '',
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Failed to log authentication: {str(e)}")
    
    def get_user_auth_history(self, user: User, limit: int = 10) -> List[FaceAuthenticationLog]:
        """Foydalanuvchi autentifikatsiya tarixini olish"""
        return FaceAuthenticationLog.objects.filter(user=user).order_by('-attempted_at')[:limit]
    
    def check_suspicious_activity(self, user: User, hours: int = 24, max_failures: int = 5) -> bool:
        """Shubhali faoliyatni tekshirish"""
        since = timezone.now() - timezone.timedelta(hours=hours)
        failures = FaceAuthenticationLog.objects.filter(
            user=user,
            status=FaceAuthenticationLog.AuthStatus.FAILED,
            attempted_at__gte=since
        ).count()
        
        return failures >= max_failures