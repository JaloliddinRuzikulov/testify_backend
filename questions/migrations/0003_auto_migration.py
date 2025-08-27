# Generated manually for migration from Subject->Topic to Fan->Paragraph->Point

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_initial'),
    ]

    operations = [
        # 1. Create new models
        migrations.CreateModel(
            name='Fan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Fan Name')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Fan Code')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Fan',
                'verbose_name_plural': 'Fanlar',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Paragraph',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Paragraph Name')),
                ('number', models.PositiveIntegerField(verbose_name='Paragraph Number')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('fan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paragraphs', to='questions.fan', verbose_name='Fan')),
            ],
            options={
                'verbose_name': 'Paragraph',
                'verbose_name_plural': 'Paragraphlar',
                'ordering': ['fan__name', 'number'],
                'unique_together': {('fan', 'number')},
            },
        ),
        migrations.CreateModel(
            name='Point',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300, verbose_name='Point Name')),
                ('number', models.PositiveIntegerField(verbose_name='Point Number')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('paragraph', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='points', to='questions.paragraph', verbose_name='Paragraph')),
            ],
            options={
                'verbose_name': 'Point',
                'verbose_name_plural': 'Pointlar',
                'ordering': ['paragraph__fan__name', 'paragraph__number', 'number'],
                'unique_together': {('paragraph', 'number')},
            },
        ),
        
        # 2. Add new fields to Question (nullable first)
        migrations.AddField(
            model_name='question',
            name='fan',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='questions.fan', verbose_name='Fan'),
        ),
        migrations.AddField(
            model_name='question',
            name='paragraph',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='questions.paragraph', verbose_name='Paragraph'),
        ),
        migrations.AddField(
            model_name='question',
            name='point',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='questions.point', verbose_name='Point'),
        ),
    ]