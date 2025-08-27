"""
Liveness Detection Service for Backend Verification
"""
import base64
import io
import hashlib
import time
from typing import Dict, Tuple, Optional
from PIL import Image
import numpy as np
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class LivenessVerificationService:
    """
    Backend service for verifying liveness of face authentication
    """
    
    # Liveness check thresholds
    MIN_IMAGE_SIZE = (200, 200)  # Minimum image dimensions
    MAX_IMAGE_SIZE = (4000, 4000)  # Maximum image dimensions
    MIN_FACE_AREA_RATIO = 0.05  # Face should be at least 5% of image
    MAX_FACE_AREA_RATIO = 0.8  # Face should not be more than 80% of image
    
    # Anti-spoofing thresholds
    MIN_IMAGE_ENTROPY = 4.0  # Minimum entropy for real image
    MAX_IMAGE_SIMILARITY = 0.95  # Maximum similarity to previous attempts
    MIN_TIME_BETWEEN_ATTEMPTS = 2  # Seconds between authentication attempts
    
    # Cache settings
    CACHE_PREFIX = 'liveness_'
    CACHE_TIMEOUT = 300  # 5 minutes
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    
    @classmethod
    def verify_liveness(cls, image_data: str, user_id: str, 
                        liveness_data: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Verify the liveness of a face authentication attempt
        
        Args:
            image_data: Base64 encoded image
            user_id: User identifier (PNFL or username)
            liveness_data: Optional liveness check data from frontend
            
        Returns:
            Tuple of (is_live, reason)
        """
        try:
            # Check for rate limiting
            if not cls._check_rate_limit(user_id):
                return False, "Juda ko'p urinish. 15 daqiqa kutib turing."
            
            # Decode and validate image
            image = cls._decode_image(image_data)
            if not image:
                return False, "Noto'g'ri rasm formati"
            
            # Basic image quality checks
            is_valid, reason = cls._validate_image_quality(image)
            if not is_valid:
                return False, reason
            
            # Check for image manipulation
            is_genuine, reason = cls._check_image_genuineness(image)
            if not is_genuine:
                return False, reason
            
            # Check against recent attempts (anti-replay)
            is_unique, reason = cls._check_uniqueness(image_data, user_id)
            if not is_unique:
                return False, reason
            
            # Verify frontend liveness data if provided
            if liveness_data:
                is_valid, reason = cls._verify_frontend_liveness(liveness_data)
                if not is_valid:
                    return False, reason
            
            # Store successful attempt
            cls._store_attempt(image_data, user_id, success=True)
            
            return True, "Tiriklik tasdiqlandi"
            
        except Exception as e:
            logger.error(f"Liveness verification error: {str(e)}")
            return False, "Tiriklik tekshiruvida xatolik"
    
    @classmethod
    def _check_rate_limit(cls, user_id: str) -> bool:
        """Check if user has exceeded rate limits"""
        lockout_key = f"{cls.CACHE_PREFIX}lockout_{user_id}"
        
        # Check if user is locked out
        if cache.get(lockout_key):
            return False
        
        # Check failed attempts
        attempts_key = f"{cls.CACHE_PREFIX}attempts_{user_id}"
        attempts = cache.get(attempts_key, 0)
        
        if attempts >= cls.MAX_FAILED_ATTEMPTS:
            # Lock out the user
            cache.set(lockout_key, True, cls.LOCKOUT_DURATION)
            cache.delete(attempts_key)
            return False
        
        return True
    
    @classmethod
    def _decode_image(cls, image_data: str) -> Optional[Image.Image]:
        """Decode base64 image data"""
        try:
            # Remove data URL prefix if present
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.error(f"Image decode error: {str(e)}")
            return None
    
    @classmethod
    def _validate_image_quality(cls, image: Image.Image) -> Tuple[bool, str]:
        """Validate basic image quality"""
        
        # Check image size
        width, height = image.size
        
        if width < cls.MIN_IMAGE_SIZE[0] or height < cls.MIN_IMAGE_SIZE[1]:
            return False, "Rasm juda kichik"
        
        if width > cls.MAX_IMAGE_SIZE[0] or height > cls.MAX_IMAGE_SIZE[1]:
            return False, "Rasm juda katta"
        
        # Check aspect ratio (should be somewhat portrait-like for face)
        aspect_ratio = width / height
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            return False, "Noto'g'ri rasm nisbati"
        
        # Check image entropy (complexity)
        entropy = cls._calculate_image_entropy(image)
        if entropy < cls.MIN_IMAGE_ENTROPY:
            return False, "Rasm sifati past yoki sun'iy"
        
        return True, "OK"
    
    @classmethod
    def _calculate_image_entropy(cls, image: Image.Image) -> float:
        """Calculate image entropy to detect uniform/artificial images"""
        try:
            # Convert to grayscale
            gray = image.convert('L')
            
            # Get histogram
            hist = gray.histogram()
            
            # Calculate entropy
            total_pixels = sum(hist)
            entropy = 0.0
            
            for count in hist:
                if count > 0:
                    probability = count / total_pixels
                    entropy -= probability * np.log2(probability)
            
            return entropy
            
        except Exception as e:
            logger.error(f"Entropy calculation error: {str(e)}")
            return 0.0
    
    @classmethod
    def _check_image_genuineness(cls, image: Image.Image) -> Tuple[bool, str]:
        """Check if image appears to be genuine (not screenshot/printed)"""
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Check for uniform borders (common in screenshots)
        border_size = 10
        top_border = img_array[:border_size, :].flatten()
        bottom_border = img_array[-border_size:, :].flatten()
        left_border = img_array[:, :border_size].flatten()
        right_border = img_array[:, -border_size:].flatten()
        
        # Calculate standard deviation of borders
        border_std = np.mean([
            np.std(top_border),
            np.std(bottom_border),
            np.std(left_border),
            np.std(right_border)
        ])
        
        # Very low standard deviation indicates uniform borders (screenshot)
        if border_std < 5:
            return False, "Rasm sun'iy ko'rinadi"
        
        # Check for noise patterns (real camera images have noise)
        noise_level = cls._estimate_noise_level(img_array)
        if noise_level < 0.5:
            return False, "Rasm kameradan olinmagan"
        
        return True, "OK"
    
    @classmethod
    def _estimate_noise_level(cls, img_array: np.ndarray) -> float:
        """Estimate image noise level"""
        try:
            # Use Laplacian to detect edges/noise
            from scipy import ndimage
            
            # Convert to grayscale if color
            if len(img_array.shape) == 3:
                gray = np.mean(img_array, axis=2)
            else:
                gray = img_array
            
            # Apply Laplacian filter
            laplacian = ndimage.laplace(gray)
            
            # Calculate noise as variance of Laplacian
            noise = np.var(laplacian)
            
            return noise
            
        except Exception as e:
            logger.error(f"Noise estimation error: {str(e)}")
            return 0.0
    
    @classmethod
    def _check_uniqueness(cls, image_data: str, user_id: str) -> Tuple[bool, str]:
        """Check if image is unique (not a replay attack)"""
        
        # Generate image hash
        image_hash = hashlib.sha256(image_data.encode()).hexdigest()
        
        # Check recent hashes
        recent_key = f"{cls.CACHE_PREFIX}recent_{user_id}"
        recent_hashes = cache.get(recent_key, [])
        
        if image_hash in recent_hashes:
            return False, "Bu rasm avval ishlatilgan"
        
        # Check time since last attempt
        last_time_key = f"{cls.CACHE_PREFIX}last_time_{user_id}"
        last_time = cache.get(last_time_key, 0)
        current_time = time.time()
        
        if current_time - last_time < cls.MIN_TIME_BETWEEN_ATTEMPTS:
            return False, "Juda tez urinish"
        
        # Update cache
        recent_hashes.append(image_hash)
        recent_hashes = recent_hashes[-10:]  # Keep last 10 hashes
        cache.set(recent_key, recent_hashes, cls.CACHE_TIMEOUT)
        cache.set(last_time_key, current_time, cls.CACHE_TIMEOUT)
        
        return True, "OK"
    
    @classmethod
    def _verify_frontend_liveness(cls, liveness_data: Dict) -> Tuple[bool, str]:
        """Verify liveness data from frontend"""
        
        # Check if required checks passed
        checks = liveness_data.get('checks', {})
        
        # At least one movement indicator required
        movement_detected = (
            checks.get('blinkDetected', False) or 
            checks.get('headMovement', False) or
            checks.get('expressionChange', False)
        )
        
        if not movement_detected:
            return False, "Tirik harakatlar aniqlanmadi"
        
        # Check confidence score
        confidence = liveness_data.get('confidence', 0)
        if confidence < 0.5:
            return False, "Tiriklik ishonchi past"
        
        # Verify face quality
        if not checks.get('faceQuality', False):
            return False, "Yuz sifati past"
        
        # Check for multiple faces (spoofing attempt)
        if checks.get('multipleFaces', False):
            return False, "Bir nechta yuz aniqlandi"
        
        return True, "OK"
    
    @classmethod
    def _store_attempt(cls, image_data: str, user_id: str, success: bool):
        """Store authentication attempt for audit"""
        
        if not success:
            # Increment failed attempts
            attempts_key = f"{cls.CACHE_PREFIX}attempts_{user_id}"
            attempts = cache.get(attempts_key, 0)
            cache.set(attempts_key, attempts + 1, cls.CACHE_TIMEOUT)
        else:
            # Clear failed attempts on success
            attempts_key = f"{cls.CACHE_PREFIX}attempts_{user_id}"
            cache.delete(attempts_key)
        
        # Log attempt
        logger.info(f"Liveness check for {user_id}: {'Success' if success else 'Failed'}")
    
    @classmethod
    def reset_user_lockout(cls, user_id: str):
        """Reset user lockout (admin function)"""
        lockout_key = f"{cls.CACHE_PREFIX}lockout_{user_id}"
        attempts_key = f"{cls.CACHE_PREFIX}attempts_{user_id}"
        
        cache.delete(lockout_key)
        cache.delete(attempts_key)
        
        logger.info(f"Reset lockout for user: {user_id}")