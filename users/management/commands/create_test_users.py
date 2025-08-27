"""
Management command to create test users with all roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users with all available roles'

    def handle(self, *args, **options):
        test_users = [
            {
                'username': 'superadmin',
                'email': 'superadmin@test.com',
                'password': 'Test@123',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': User.Role.SUPERADMIN,
                'pnfl': '12345678901111',
                'is_staff': True,
                'is_superuser': True
            },
            {
                'username': 'admin',
                'email': 'admin@test.com',
                'password': 'Test@123',
                'first_name': 'Book',
                'last_name': 'Expert',
                'role': User.Role.ADMIN,
                'pnfl': '12345678902222',
                'is_staff': True,
                'is_superuser': False
            },
            {
                'username': 'qb_expert',
                'email': 'qb_expert@test.com',
                'password': 'Test@123',
                'first_name': 'QB',
                'last_name': 'Expert',
                'role': User.Role.QB_EXPERT,
                'pnfl': '12345678903333',
                'is_staff': False,
                'is_superuser': False
            },
            {
                'username': 'q_expert',
                'email': 'q_expert@test.com',
                'password': 'Test@123',
                'first_name': 'Question',
                'last_name': 'Expert',
                'role': User.Role.Q_EXPERT,
                'pnfl': '12345678904444',
                'is_staff': False,
                'is_superuser': False
            },
            {
                'username': 'creator',
                'email': 'creator@test.com',
                'password': 'Test@123',
                'first_name': 'Q',
                'last_name': 'Creator',
                'role': User.Role.CREATOR,
                'pnfl': '12345678905555',
                'is_staff': False,
                'is_superuser': False
            }
        ]

        with transaction.atomic():
            for user_data in test_users:
                username = user_data['username']
                
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.WARNING(f'User {username} already exists, skipping...')
                    )
                    continue
                
                # Extract password before creating user
                password = user_data.pop('password')
                
                # Create user
                user = User.objects.create(**user_data)
                user.set_password(password)
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created user: {username} with role: {user.get_role_display()}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS('\n✅ Test users created successfully!')
        )
        self.stdout.write(
            self.style.SUCCESS('\n📝 Login credentials:')
        )
        self.stdout.write(
            self.style.SUCCESS('   Username: [role_name]')
        )
        self.stdout.write(
            self.style.SUCCESS('   Password: Test@123')
        )
        self.stdout.write(
            self.style.SUCCESS('\n👥 Available users:')
        )
        for user_data in test_users:
            self.stdout.write(
                self.style.SUCCESS(f'   - {user_data["username"]}')
            )