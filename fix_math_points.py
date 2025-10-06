#!/usr/bin/env python
"""
Script to fix Matematika fan structure - add missing points
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from questions.models import Fan, Paragraph, Point

def fix_math_points():
    """Add missing points to Matematika paragraphs"""

    # Get Matematika fan
    try:
        fan = Fan.objects.get(name="Matematika")
    except Fan.DoesNotExist:
        print("Matematika fan not found!")
        return

    print(f"Fixing structure for fan: {fan.name}")

    # Get all paragraphs for this fan
    paragraphs = Paragraph.objects.filter(fan=fan).order_by('number')

    if not paragraphs.exists():
        print("No paragraphs found for Matematika!")
        return

    for paragraph in paragraphs:
        # Check if points already exist
        existing_points = Point.objects.filter(paragraph=paragraph)

        if existing_points.exists():
            print(f"  Paragraph '{paragraph.name}' already has {existing_points.count()} points")
        else:
            print(f"  Creating points for paragraph: {paragraph.name}")

            # Create 3-4 points for each paragraph
            points_count = 4 if paragraph.number <= 3 else 3
            for pt_num in range(1, points_count + 1):
                point = Point.objects.create(
                    paragraph=paragraph,
                    number=pt_num,
                    name=f"{paragraph.number}.{pt_num}-mavzu",
                    description=f"{paragraph.name}ning {pt_num}-mavzusi"
                )
                print(f"    Created point: {point.name}")

    print("\n✅ Matematika structure fixed successfully!")

    # Show summary
    print("\n📊 Summary for Matematika:")
    paragraphs = Paragraph.objects.filter(fan=fan)
    total_points = Point.objects.filter(paragraph__fan=fan).count()
    print(f"  Total: {paragraphs.count()} paragraphs, {total_points} points")

    # Show detailed structure
    print("\n📋 Detailed structure:")
    for paragraph in paragraphs.order_by('number'):
        points = Point.objects.filter(paragraph=paragraph).order_by('number')
        print(f"  {paragraph.number}. {paragraph.name} ({points.count()} points)")
        for point in points:
            print(f"    - {point.number}. {point.name}")

if __name__ == '__main__':
    fix_math_points()
