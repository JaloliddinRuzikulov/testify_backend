from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import base64
import secrets
import json
from .webauthn_models import WebAuthnCredential, WebAuthnChallenge
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def generate_challenge():
    """Generate a random challenge for WebAuthn"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_webauthn_start(request):
    """Start WebAuthn registration process"""
    user = request.user
    
    # Generate challenge
    challenge = generate_challenge()
    
    # Save challenge
    WebAuthnChallenge.objects.create(
        user=user,
        challenge=challenge
    )
    
    # Clean old challenges
    old_time = timezone.now() - timedelta(minutes=5)
    WebAuthnChallenge.objects.filter(created_at__lt=old_time).delete()
    
    # Prepare registration options
    registration_options = {
        'challenge': challenge,
        'rp': {
            'name': 'DTM Test Platform',
            'id': request.get_host().split(':')[0]  # Remove port if present
        },
        'user': {
            'id': base64.urlsafe_b64encode(str(user.id).encode()).decode('utf-8').rstrip('='),
            'name': user.username,
            'displayName': user.get_full_name() or user.username
        },
        'pubKeyCredParams': [
            {'type': 'public-key', 'alg': -7},   # ES256
            {'type': 'public-key', 'alg': -257}  # RS256
        ],
        'authenticatorSelection': {
            'authenticatorAttachment': 'platform',  # Use platform authenticator (FaceID/TouchID)
            'userVerification': 'required',
            'residentKey': 'preferred'
        },
        'timeout': 60000,
        'attestation': 'none'
    }
    
    return Response(registration_options)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_webauthn_finish(request):
    """Complete WebAuthn registration"""
    user = request.user
    credential_data = request.data
    
    # Verify challenge
    challenge = credential_data.get('challenge')
    challenge_obj = WebAuthnChallenge.objects.filter(
        user=user,
        challenge=challenge,
        is_used=False
    ).first()
    
    if not challenge_obj:
        return Response(
            {'error': 'Invalid or expired challenge'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Mark challenge as used
    challenge_obj.is_used = True
    challenge_obj.save()
    
    # Save credential
    credential = WebAuthnCredential.objects.create(
        user=user,
        credential_id=credential_data.get('credentialId'),
        public_key=credential_data.get('publicKey'),
        device_type=credential_data.get('deviceType', 'platform'),
        device_name=credential_data.get('deviceName', 'FaceID/TouchID')
    )
    
    return Response({
        'success': True,
        'message': 'Biometric authentication registered successfully'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def login_webauthn_start(request):
    """Start WebAuthn login process"""
    username = request.data.get('username')
    
    if not username:
        return Response(
            {'error': 'Username required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.filter(username=username).first()
    if not user:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get user's credentials
    credentials = WebAuthnCredential.objects.filter(user=user)
    if not credentials.exists():
        return Response(
            {'error': 'No biometric credentials registered'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate challenge
    challenge = generate_challenge()
    
    # Save challenge
    WebAuthnChallenge.objects.create(
        user=user,
        challenge=challenge
    )
    
    # Prepare authentication options
    auth_options = {
        'challenge': challenge,
        'rpId': request.get_host().split(':')[0],
        'allowCredentials': [
            {
                'type': 'public-key',
                'id': cred.credential_id
            }
            for cred in credentials
        ],
        'userVerification': 'required',
        'timeout': 60000
    }
    
    return Response(auth_options)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_webauthn_finish(request):
    """Complete WebAuthn login"""
    credential_data = request.data
    
    # Find credential
    credential_id = credential_data.get('credentialId')
    credential = WebAuthnCredential.objects.filter(
        credential_id=credential_id
    ).first()
    
    if not credential:
        return Response(
            {'error': 'Invalid credential'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify challenge
    challenge = credential_data.get('challenge')
    challenge_obj = WebAuthnChallenge.objects.filter(
        user=credential.user,
        challenge=challenge,
        is_used=False
    ).first()
    
    if not challenge_obj:
        return Response(
            {'error': 'Invalid or expired challenge'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Mark challenge as used
    challenge_obj.is_used = True
    challenge_obj.save()
    
    # Update credential usage
    credential.last_used = timezone.now()
    credential.sign_count += 1
    credential.save()
    
    # Generate JWT tokens
    user = credential.user
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'is_expert': user.is_expert,
            'is_creator': user.is_creator,
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_webauthn_credentials(request):
    """List user's WebAuthn credentials"""
    credentials = WebAuthnCredential.objects.filter(user=request.user)
    
    data = [
        {
            'id': cred.id,
            'device_name': cred.device_name,
            'device_type': cred.device_type,
            'created_at': cred.created_at,
            'last_used': cred.last_used
        }
        for cred in credentials
    ]
    
    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_webauthn_credential(request, credential_id):
    """Delete a WebAuthn credential"""
    try:
        credential = WebAuthnCredential.objects.get(
            id=credential_id,
            user=request.user
        )
        credential.delete()
        return Response({'success': True})
    except WebAuthnCredential.DoesNotExist:
        return Response(
            {'error': 'Credential not found'},
            status=status.HTTP_404_NOT_FOUND
        )