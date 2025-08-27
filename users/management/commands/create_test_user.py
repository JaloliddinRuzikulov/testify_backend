from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import base64
import numpy as np

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test user with face descriptor'

    def handle(self, *args, **options):
        # Create or get test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'role': User.Role.ADMIN,
            }
        )
        
        if created:
            user.set_password('testpass123')
            
        # Create dummy face descriptor (128D vector)
        # In production, this would be real face data
        dummy_descriptor = np.random.randn(128).astype(np.float32)
        
        # Convert to base64
        face_descriptor_base64 = base64.b64encode(dummy_descriptor.tobytes()).decode('utf-8')
        
        # Save face descriptor
        user.face_descriptor = face_descriptor_base64
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Test user created: {user.username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Test user updated: {user.username}'))
        
        self.stdout.write(self.style.SUCCESS('Face descriptor added successfully'))