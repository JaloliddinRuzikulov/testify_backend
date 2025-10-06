from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, CustomTokenObtainPairView
from .webauthn_views import (
    register_webauthn_start,
    register_webauthn_finish,
    login_webauthn_start,
    login_webauthn_finish,
    list_webauthn_credentials,
    delete_webauthn_credential
)
from .face_auth_views import (
    FaceAuthRegisterView,
    FaceAuthLoginView,
    VerifyPassportView,
    FaceAuthHistoryView,
    UpdateFaceDescriptorView,
    FetchPassportDataView,
    EnhancedFaceAuthRegisterView,
)
from .government_passport_views import (
    CheckPersonalizationView,
    GovernmentFaceLoginView,
    GetUserProfileView,
    LinkUserToPassportView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Face Authentication endpoints
    path('auth/face/register/', FaceAuthRegisterView.as_view(), name='face_auth_register'),
    path('auth/face/login/', FaceAuthLoginView.as_view(), name='face_auth_login'),
    path('auth/face/verify-passport/', VerifyPassportView.as_view(), name='verify_passport'),
    path('auth/face/history/', FaceAuthHistoryView.as_view(), name='face_auth_history'),
    path('auth/face/update-descriptor/', UpdateFaceDescriptorView.as_view(), name='update_face_descriptor'),
    path('auth/face/fetch-passport/', FetchPassportDataView.as_view(), name='fetch_passport_data'),
    path('auth/face/enhanced-register/', EnhancedFaceAuthRegisterView.as_view(), name='enhanced_face_register'),
    
    # Government Passport API endpoints
    path('government/check-personalization/', CheckPersonalizationView.as_view(), name='check_personalization'),
    path('government/face-login/', GovernmentFaceLoginView.as_view(), name='government_face_login'),
    path('government/profile/', GetUserProfileView.as_view(), name='get_user_profile'),
    path('government/link-user/', LinkUserToPassportView.as_view(), name='link_user_to_passport'),
]