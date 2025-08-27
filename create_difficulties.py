#!/usr/bin/env python
"""
Script to create default difficulty levels
"""
import os
import sys
import django

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_platform.settings')
django.setup()

from questions.models import Difficulty

def create_difficulties():
    """Create default difficulty levels"""
    
    difficulties = [
        {
            'name': 'Oson',
            'code': 'EASY',
            'level': 1,
            'description': 'Oddiy darajadagi savollar'
        },
        {
            'name': "O'rta",
            'code': 'MEDIUM',
            'level': 2,
            'description': "O'rtacha qiyinlikdagi savollar"
        },
        {
            'name': 'Qiyin',
            'code': 'HARD',
            'level': 3,
            'description': 'Yuqori darajadagi murakkab savollar'
        },
        {
            'name': 'Juda qiyin',
            'code': 'VERY_HARD',
            'level': 4,
            'description': 'Eng yuqori darajadagi savollar'
        }
    ]
    
    for diff_data in difficulties:
        difficulty, created = Difficulty.objects.get_or_create(
            code=diff_data['code'],
            defaults=diff_data
        )
        if created:
            print(f"✅ Created difficulty: {difficulty.name}")
        else:
            print(f"ℹ️ Difficulty already exists: {difficulty.name}")

if __name__ == '__main__':
    create_difficulties()
    print("✅ All difficulties created successfully!")