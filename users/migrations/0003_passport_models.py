# Generated migration for passport models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_face_descriptor_webauthncredential_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PassportData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('passport_series', models.CharField(max_length=10, verbose_name='Passport seriyasi')),
                ('passport_number', models.CharField(max_length=20, verbose_name='Passport raqami')),
                ('pinfl', models.CharField(max_length=14, unique=True, verbose_name='PINFL/JSHSHIR')),
                ('first_name', models.CharField(max_length=100, verbose_name='Ism')),
                ('last_name', models.CharField(max_length=100, verbose_name='Familiya')),
                ('middle_name', models.CharField(blank=True, max_length=100, verbose_name='Otasining ismi')),
                ('birth_date', models.DateField(verbose_name="Tug'ilgan sana")),
                ('photo_base64', models.TextField(help_text='Base64 formatdagi passport rasmi', verbose_name='Passport rasmi (Base64)')),
                ('face_descriptors', models.JSONField(blank=True, help_text="Yuzni tanish uchun kerakli ma'lumotlar", null=True, verbose_name='Face descriptors')),
                ('address', models.TextField(blank=True, verbose_name='Manzil')),
                ('issued_by', models.CharField(blank=True, max_length=200, verbose_name='Kim tomonidan berilgan')),
                ('issue_date', models.DateField(blank=True, null=True, verbose_name='Berilgan sana')),
                ('expire_date', models.DateField(blank=True, null=True, verbose_name='Amal qilish muddati')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': "Passport ma'lumoti",
                'verbose_name_plural': "Passport ma'lumotlari",
                'indexes': [
                    models.Index(fields=['pinfl'], name='users_passpo_pinfl_idx'),
                    models.Index(fields=['passport_series', 'passport_number'], name='users_passpo_series_num_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='UserPassportLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verified', models.BooleanField(default=False, verbose_name='Tasdiqlangan')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='Tasdiqlangan vaqt')),
                ('face_match_score', models.FloatField(blank=True, help_text="0-1 oralig'ida, 0.8+ yuqori moslik", null=True, verbose_name='Yuz moslik darajasi')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('passport_data', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_links', to='users.passportdata', verbose_name="Passport ma'lumoti")),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='passport_link', to='users.user', verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': "User-Passport bog'lanish",
                'verbose_name_plural': "User-Passport bog'lanishlar",
            },
        ),
        migrations.CreateModel(
            name='FaceAuthenticationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('SUCCESS', 'Muvaffaqiyatli'), ('FAILED', 'Muvaffaqiyatsiz'), ('NO_FACE', 'Yuz topilmadi'), ('MULTIPLE_FACES', 'Bir nechta yuz topildi'), ('LOW_QUALITY', 'Past sifat'), ('TIMEOUT', 'Vaqt tugadi')], max_length=20, verbose_name='Holat')),
                ('match_score', models.FloatField(blank=True, null=True, verbose_name='Moslik darajasi')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP manzil')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('error_message', models.TextField(blank=True, verbose_name='Xatolik xabari')),
                ('attempted_at', models.DateTimeField(auto_now_add=True, verbose_name='Urinish vaqti')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='face_auth_logs', to='users.user', verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'Face Auth log',
                'verbose_name_plural': 'Face Auth loglar',
                'ordering': ['-attempted_at'],
                'indexes': [
                    models.Index(fields=['user', '-attempted_at'], name='users_faceauth_user_time_idx'),
                    models.Index(fields=['status', '-attempted_at'], name='users_faceauth_status_time_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='passportdata',
            unique_together={('passport_series', 'passport_number')},
        ),
    ]