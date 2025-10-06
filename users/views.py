from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer,
    FaceRegistrationSerializer,
    FaceLoginSerializer
)
from .permissions import IsAdminOrSelf, IsAdmin

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view with additional user info"""
    # permission_class = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management"""
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrSelf()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """
        Create user with government passport integration

        Expected payload:
        {
            "pnfl": "12345678901234",
            "passport": "AA1234567",
            "role": "CREATOR",
            "expert_subject": 1  # optional, for Q_EXPERT role
        }

        Process:
        1. Get data from government API
        2. Create or update PassportData
        3. Create User with auto-generated username/email
        4. Link User to PassportData via UserPassportLink
        """
        from .government_passport_service import get_government_passport_service
        from .passport_models import PassportData, UserPassportLink
        from django.utils import timezone
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)

        # Get request data
        pnfl = request.data.get('pnfl')
        passport = request.data.get('passport')
        role = request.data.get('role', 'CREATOR')
        expert_subject = request.data.get('expert_subject')

        # Validate required fields
        if not pnfl or not passport:
            return Response(
                {'error': 'PNFL va passport majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get data from government API
        logger.info(f"Fetching government data for PNFL: {pnfl}, Passport: {passport}")
        gov_service = get_government_passport_service()
        gov_data = gov_service.get_passport_data(pnfl, passport)

        if gov_data.get('status') != 1:
            return Response(
                {'error': gov_data.get('message', 'Passport ma\'lumotlari topilmadi')},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = gov_data['data']
        logger.info(f"Successfully retrieved government data for {data.get('fname')} {data.get('sname')}")

        # Check if user already exists with this PNFL
        existing_user = User.objects.filter(pnfl=pnfl).first()
        if existing_user:
            return Response(
                {'error': 'Bu PNFL bilan foydalanuvchi allaqachon mavjud'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse dates
        try:
            birth_date = datetime.strptime(data.get('birth_date'), '%Y-%m-%d').date()
            issue_date = datetime.strptime(data.get('matches_date_begin_document'), '%Y-%m-%d').date()
            expire_date = datetime.strptime(data.get('matches_date_end_document'), '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            logger.error(f"Date parsing error: {e}")
            birth_date = None
            issue_date = None
            expire_date = None

        # Create or update PassportData
        passport_data, created = PassportData.objects.update_or_create(
            pinfl=pnfl,
            defaults={
                'passport_series': data.get('ps_ser', passport[:2]),
                'passport_number': data.get('ps_num', passport[2:]),
                'first_name': data.get('fname', ''),
                'last_name': data.get('sname', ''),
                'middle_name': data.get('mname', ''),
                'birth_date': birth_date,
                'photo_base64': data.get('photo', ''),
                'issued_by': data.get('doc_give_place', ''),
                'issue_date': issue_date,
                'expire_date': expire_date,
            }
        )
        logger.info(f"PassportData {'created' if created else 'updated'} for PNFL: {pnfl}")

        # Generate username from PNFL
        username = f"user_{pnfl}"
        email = f"{username}@dtm.uz"

        # Create User
        user = User.objects.create(
            username=username,
            email=email,
            first_name=data.get('fname', ''),
            last_name=data.get('sname', ''),
            pnfl=pnfl,
            passport=passport,
            role=role,
            is_active=True
        )
        user.set_unusable_password()  # No password, face auth only
        user.save()

        # Set expert_subject if Q_EXPERT
        if role == 'Q_EXPERT' and expert_subject:
            from questions.models import Subject
            try:
                subject = Subject.objects.get(id=expert_subject)
                user.expert_subject = subject
                user.save()
            except Subject.DoesNotExist:
                logger.warning(f"Subject {expert_subject} not found")

        logger.info(f"User created: {username} with role {role}")

        # Create UserPassportLink
        user_passport_link = UserPassportLink.objects.create(
            user=user,
            passport_data=passport_data,
            verified=True,
            verified_at=timezone.now()
        )
        logger.info(f"UserPassportLink created for user {username}")

        # Return response
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """Change user password"""
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"status": "password changed successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register_face(self, request):
        """Register face descriptor for current user"""
        serializer = FaceRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.face_descriptor = serializer.validated_data['face_descriptor']
            user.save(update_fields=['face_descriptor'])
            return Response({"status": "Face registered successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def face_login(self, request):
        """Authenticate user with face descriptor"""
        import base64
        import numpy as np
        from rest_framework_simplejwt.tokens import RefreshToken
        
        serializer = FaceLoginSerializer(data=request.data)
        if serializer.is_valid():
            face_descriptor = serializer.validated_data['face_descriptor']
            
            # Find matching user by comparing face descriptors
            users_with_faces = User.objects.exclude(face_descriptor__isnull=True).exclude(face_descriptor='')
            
            for user in users_with_faces:
                # Compare face descriptors (simplified - in production use proper face comparison)
                try:
                    # Decode base64 descriptors
                    input_desc = np.frombuffer(base64.b64decode(face_descriptor), dtype=np.float32)
                    stored_desc = np.frombuffer(base64.b64decode(user.face_descriptor), dtype=np.float32)
                    
                    # Calculate Euclidean distance
                    distance = np.linalg.norm(input_desc - stored_desc)
                    
                    # Threshold for matching (adjust based on testing)
                    if distance < 0.6:
                        # Generate tokens
                        refresh = RefreshToken.for_user(user)
                        return Response({
                            'access': str(refresh.access_token),
                            'refresh': str(refresh),
                            'user': UserSerializer(user).data
                        })
                except Exception as e:
                    continue
            
            return Response(
                {"error": "No matching face found"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
