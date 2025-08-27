# Remove old Subject and Topic fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0004_migrate_data'),
    ]

    operations = [
        # Make new fields non-nullable
        migrations.AlterField(
            model_name='question',
            name='fan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='questions.fan', verbose_name='Fan'),
        ),
        migrations.AlterField(
            model_name='question',
            name='paragraph',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='questions.paragraph', verbose_name='Paragraph'),
        ),
        
        # Remove old fields
        migrations.RemoveField(
            model_name='question',
            name='subject',
        ),
        migrations.RemoveField(
            model_name='question',
            name='topic',
        ),
        
        # Delete old models
        migrations.DeleteModel(
            name='Topic',
        ),
        migrations.DeleteModel(
            name='Subject',
        ),
    ]