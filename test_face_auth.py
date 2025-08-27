#!/usr/bin/env python
"""Test face authentication with real government data"""

import os
import sys
import django
import requests
import json

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_platform.settings')
django.setup()

from users.models import User
from users.face_auth_service import FaceAuthenticationService

# Real ma'lumotlar
PNFL = "51304025740014"
PASSPORT = "AC1987867"
USERNAME = "jaloliddin_admin"

print("Testing face authentication with real government data")
print("="*60)

try:
    # User olish
    user = User.objects.get(username=USERNAME)
    print(f"✅ User found: {user.username}")
    print(f"   PNFL: {user.pnfl}")
    print(f"   Passport: {user.passport}")
    
    # Face service
    face_service = FaceAuthenticationService()
    
    # Test image (mock, chunki real camera yo'q)
    test_face_image = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAr/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCywAE//9k="
    
    # Face verification
    result = face_service.verify_user_face(
        user=user,
        face_image_base64=test_face_image,
        ip_address="127.0.0.1",
        user_agent="Test Script"
    )
    
    print("\n" + "="*60)
    print("FACE AUTHENTICATION RESULT:")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Match Score: {result['match_score']:.2%}")
    print(f"Status: {result['status']}")
    
    if result['success']:
        print("\n✅ FACE AUTHENTICATION SUCCESSFUL!")
        print("User can login to the system.")
    else:
        print("\n❌ FACE AUTHENTICATION FAILED!")
        print(f"Reason: {result['message']}")
    
    print("="*60)
    
    # Check if using mock implementation
    if not face_service.face_cascade:
        print("\n⚠️  Note: Using MOCK face recognition implementation")
        print("   (face_recognition library not installed)")
        print("   Mock always returns 85% match for testing")
    
except User.DoesNotExist:
    print(f"❌ User not found: {USERNAME}")
    print("   Run create_real_admin.py first")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()