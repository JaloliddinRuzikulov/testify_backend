# Data migration to convert Subject->Topic to Fan->Paragraph

from django.db import migrations


def migrate_subjects_to_fans(apps, schema_editor):
    Subject = apps.get_model('questions', 'Subject')
    Topic = apps.get_model('questions', 'Topic')
    Fan = apps.get_model('questions', 'Fan')
    Paragraph = apps.get_model('questions', 'Paragraph')
    Question = apps.get_model('questions', 'Question')
    
    # Create Fan from Subject
    for subject in Subject.objects.all():
        fan = Fan.objects.create(
            name=subject.name,
            code=subject.code,
            description=subject.description
        )
        
        # Create Paragraphs from Topics
        topics = Topic.objects.filter(subject=subject)
        for idx, topic in enumerate(topics, start=1):
            paragraph = Paragraph.objects.create(
                fan=fan,
                name=topic.name,
                number=idx,
                description=topic.description
            )
            
            # Update questions to use new Fan and Paragraph
            questions = Question.objects.filter(subject=subject, topic=topic)
            questions.update(fan=fan, paragraph=paragraph)


def reverse_migration(apps, schema_editor):
    # This is a destructive migration, so reverse is not implemented
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0003_auto_migration'),
    ]

    operations = [
        migrations.RunPython(migrate_subjects_to_fans, reverse_migration),
    ]