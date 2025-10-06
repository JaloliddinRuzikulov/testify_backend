#!/usr/bin/env python
"""
Script to create test fan structure (paragraphs and points)
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from questions.models import Fan, Paragraph, Point

def create_test_structure():
    """Create test paragraphs and points for existing fans"""

    # Get all fans
    fans = Fan.objects.all()

    if not fans.exists():
        print("No fans found. Creating test fan...")
        fan = Fan.objects.create(
            name="Matematika",
            code="MATH",
            description="Matematika fani"
        )
        fans = [fan]

    for fan in fans:
        print(f"\nCreating structure for fan: {fan.name}")

        # Check if paragraphs already exist
        existing_paragraphs = Paragraph.objects.filter(fan=fan)
        if existing_paragraphs.exists():
            print(f"  Paragraphs already exist for {fan.name}")
            continue

        # Create 3 paragraphs for each fan
        for p_num in range(1, 4):
            paragraph = Paragraph.objects.create(
                fan=fan,
                number=p_num,
                name=f"{fan.name} - {p_num}-bo'lim",
                description=f"{fan.name} fanining {p_num}-bo'limi"
            )
            print(f"  Created paragraph: {paragraph.name}")

            # Create 3-4 points for each paragraph
            points_count = 4 if p_num == 1 else 3
            for pt_num in range(1, points_count + 1):
                point = Point.objects.create(
                    paragraph=paragraph,
                    number=pt_num,
                    name=f"{p_num}.{pt_num}-mavzu",
                    description=f"{paragraph.name}ning {pt_num}-mavzusi"
                )
                print(f"    Created point: {point.name}")

    print("\n✅ Test structure created successfully!")

    # Show summary
    print("\n📊 Summary:")
    for fan in Fan.objects.all():
        paragraphs = Paragraph.objects.filter(fan=fan)
        total_points = Point.objects.filter(paragraph__fan=fan).count()
        print(f"  {fan.name}: {paragraphs.count()} paragraphs, {total_points} points")

if __name__ == '__main__':
    create_test_structure()
