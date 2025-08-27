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
