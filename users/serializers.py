from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user info"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra user information to response
        data.update({
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
        })
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""
    expert_subject_name = serializers.CharField(source='expert_subject.name', read_only=True)
    profile_image = serializers.ImageField(read_only=False, required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'bio', 'profile_image', 'date_joined', 
            'expert_subject', 'expert_subject_name'
        )
        read_only_fields = ('id', 'date_joined')
    
    def to_representation(self, instance):
        """Override to add full URL for profile_image and fetch passport photo if needed"""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        # If profile_image exists, return its full URL
        if instance.profile_image and request:
            representation['profile_image'] = request.build_absolute_uri(instance.profile_image.url)
        # If no profile_image but has passport data, try to fetch from government API
        elif instance.pnfl and instance.passport and not instance.profile_image:
            from .government_passport_service import GovernmentPassportService
            import base64
            from django.core.files.base import ContentFile
            import logging
            
            logger = logging.getLogger(__name__)
            
            try:
                # Get passport photo from government API
                service = GovernmentPassportService()
                passport_data = service.get_passport_data(instance.pnfl, instance.passport)
                
                if passport_data.get('status') == 1 and passport_data.get('data', {}).get('photo'):
                    photo_base64 = passport_data['data']['photo']
                    
                    # Remove data:image prefix if exists
                    if photo_base64.startswith('data:image'):
                        photo_base64 = photo_base64.split(',')[1]
                    
                    # Save photo to profile_image field
                    photo_data = base64.b64decode(photo_base64)
                    photo_file = ContentFile(photo_data, name=f'passport_{instance.username}.jpg')
                    instance.profile_image.save(f'passport_{instance.username}.jpg', photo_file, save=True)
                    
                    # Return the new profile_image URL
                    if request:
                        representation['profile_image'] = request.build_absolute_uri(instance.profile_image.url)
                    
                    logger.info(f"Successfully saved passport photo for user {instance.username}")
            except Exception as e:
                logger.error(f"Error fetching passport photo for user {instance.username}: {str(e)}")
        
        return representation


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users - with face auth support"""

    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        allow_blank=True
    )
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)
    passport_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'pnfl', 'passport',
            'passport_photo', 'expert_subject'
        )

    def validate(self, data):
        # If password provided, check confirmation
        if data.get('password') and data.get('password_confirm'):
            if data['password'] != data['password_confirm']:
                raise serializers.ValidationError({
                    "password": "Password fields didn't match."
                })

        # If no password, username will be auto-generated from PINFL
        if not data.get('username') and data.get('pnfl'):
            data['username'] = f"user_{data['pnfl']}"

        # Email can be auto-generated if not provided
        if not data.get('email'):
            data['email'] = f"{data.get('username', 'user')}@dtm.uz"

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        validated_data.pop('passport_photo', None)  # Handled separately

        password = validated_data.pop('password', None)

        if password:
            user = User.objects.create_user(**validated_data, password=password)
        else:
            # Create user without password (face auth only)
            user = User.objects.create(**validated_data)
            user.set_unusable_password()
            user.save()

        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password": "Password fields didn't match."
            })
        return data


class FaceRegistrationSerializer(serializers.Serializer):
    """Serializer for face registration"""
    face_descriptor = serializers.CharField(required=True)
    
    def validate_face_descriptor(self, value):
        if not value:
            raise serializers.ValidationError("Face descriptor is required")
        # Validate it's base64 encoded
        import base64
        try:
            base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError("Invalid face descriptor format")
        return value


class FaceLoginSerializer(serializers.Serializer):
    """Serializer for face authentication"""
    face_descriptor = serializers.CharField(required=True)
    
    def validate_face_descriptor(self, value):
        if not value:
            raise serializers.ValidationError("Face descriptor is required")
        import base64
        try:
            base64.b64decode(value)
        except Exception:
            raise serializers.ValidationError("Invalid face descriptor format")
        return value