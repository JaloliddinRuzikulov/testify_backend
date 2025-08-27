from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import base64
import json


class PassportData(models.Model):
    """Passport ma'lumotlar modeli - Tashqi passport bazasidan olinadi"""
    
    passport_series = models.CharField(
        max_length=10,
        verbose_name=_('Passport seriyasi')
    )
    passport_number = models.CharField(
        max_length=20,
        verbose_name=_('Passport raqami')
    )
    pinfl = models.CharField(
        max_length=14,
        unique=True,
        verbose_name=_('PINFL/JSHSHIR')
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name=_('Ism')
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_('Familiya')
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Otasining ismi')
    )
    birth_date = models.DateField(
        verbose_name=_('Tug\'ilgan sana')
    )
    photo_base64 = models.TextField(
        verbose_name=_('Passport rasmi (Base64)'),
        help_text=_('Base64 formatdagi passport rasmi')
    )
    face_descriptors = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Face descriptors'),
        help_text=_('Yuzni tanish uchun kerakli ma\'lumotlar')
    )
    
    # Qo'shimcha ma'lumotlar
    address = models.TextField(
        blank=True,
        verbose_name=_('Manzil')
    )
    issued_by = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Kim tomonidan berilgan')
    )
    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Berilgan sana')
    )
    expire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Amal qilish muddati')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Passport ma\'lumoti')
        verbose_name_plural = _('Passport ma\'lumotlari')
        unique_together = ['passport_series', 'passport_number']
        indexes = [
            models.Index(fields=['pinfl']),
            models.Index(fields=['passport_series', 'passport_number']),
        ]
    
    def __str__(self):
        return f"{self.passport_series}{self.passport_number} - {self.first_name} {self.last_name}"
    
    def get_photo_as_image(self):
        """Base64 rasmni PIL Image obyektiga aylantirish"""
        from PIL import Image
        from io import BytesIO
        
        if self.photo_base64:
            # Base64 prefiksni olib tashlash
            if ',' in self.photo_base64:
                image_data = self.photo_base64.split(',')[1]
            else:
                image_data = self.photo_base64
            
            image_bytes = base64.b64decode(image_data)
            return Image.open(BytesIO(image_bytes))
        return None


class UserPassportLink(models.Model):
    """User va Passport ma'lumotlarini bog'lash"""
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='passport_link',
        verbose_name=_('Foydalanuvchi')
    )
    passport_data = models.ForeignKey(
        PassportData,
        on_delete=models.PROTECT,
        related_name='user_links',
        verbose_name=_('Passport ma\'lumoti')
    )
    verified = models.BooleanField(
        default=False,
        verbose_name=_('Tasdiqlangan')
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Tasdiqlangan vaqt')
    )
    face_match_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Yuz moslik darajasi'),
        help_text=_('0-1 oralig\'ida, 0.8+ yuqori moslik')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User-Passport bog\'lanish')
        verbose_name_plural = _('User-Passport bog\'lanishlar')
    
    def __str__(self):
        return f"{self.user.username} - {self.passport_data.pinfl}"


# Validators
pnfl_regex = RegexValidator(
    regex=r'^[0-9]{14}$',
    message="PNFL 14 ta raqamdan iborat bo'lishi kerak."
)


class UserProfile(models.Model):
    """
    To'liq passport ma'lumotlari (Government API'dan olinadi)
    Certificate verification tizimidan olingan model
    """
    
    # User relationship
    user = models.OneToOneField(
        'User',
        on_delete=models.SET_NULL,
        related_name='full_profile',
        null=True,
        blank=True,
        verbose_name=_('Foydalanuvchi')
    )
    
    # Passport ma'lumotlari
    ps_ser = models.CharField(
        max_length=3,
        verbose_name=_('Passport seriyasi')
    )
    ps_num = models.CharField(
        max_length=10,
        verbose_name=_('Passport raqami')
    )
    pnfl = models.BigIntegerField(
        validators=[pnfl_regex],
        unique=True,
        verbose_name=_('PINFL/JSHSHIR')
    )
    
    # Shaxsiy ma'lumotlar
    sname = models.CharField(
        max_length=63,
        verbose_name=_('Familiya')
    )
    fname = models.CharField(
        max_length=63,
        verbose_name=_('Ism')
    )
    mname = models.CharField(
        max_length=63,
        verbose_name=_('Otasining ismi')
    )
    
    # Tug'ilgan joy va sana
    birth_place = models.CharField(
        max_length=127,
        verbose_name=_('Tug\'ilgan joy')
    )
    birth_date = models.DateField(
        verbose_name=_('Tug\'ilgan sana')
    )
    birth_country = models.CharField(
        max_length=127,
        verbose_name=_('Tug\'ilgan davlat')
    )
    birth_country_id = models.IntegerField(
        verbose_name=_('Tug\'ilgan davlat ID')
    )
    
    # Status va ma'lumotlar
    livestatus = models.CharField(
        max_length=1,
        choices=[('0', 'Tirik'), ('1', 'Vafot etgan')],
        default='0',
        verbose_name=_('Hayot holati')
    )
    nationality = models.CharField(
        max_length=127,
        verbose_name=_('Millati')
    )
    nationality_id = models.IntegerField(
        verbose_name=_('Millat ID')
    )
    sex = models.CharField(
        max_length=1,
        choices=[('1', 'Erkak'), ('2', 'Ayol')],
        verbose_name=_('Jinsi')
    )
    
    # Passport berilgan joy va muddatlar
    doc_give_place = models.CharField(
        max_length=255,
        verbose_name=_('Passport berilgan joy')
    )
    doc_give_place_id = models.IntegerField(
        verbose_name=_('Passport berilgan joy ID')
    )
    matches_date_begin_document = models.DateField(
        verbose_name=_('Passport berilgan sana')
    )
    matches_date_end_document = models.DateField(
        verbose_name=_('Passport amal qilish muddati')
    )
    
    # Foto (Base64)
    photo = models.TextField(
        verbose_name=_('Passport rasmi (Base64)'),
        help_text=_('Government API\'dan olingan rasm')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Verification status
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('Tasdiqlangan')
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Tasdiqlangan vaqt')
    )
    
    class Meta:
        verbose_name = _('Foydalanuvchi profili')
        verbose_name_plural = _('Foydalanuvchi profillari')
        indexes = [
            models.Index(fields=['pnfl']),
            models.Index(fields=['ps_ser', 'ps_num']),
        ]
    
    def __str__(self):
        return f"{self.sname} {self.fname} - {self.ps_ser}{self.ps_num}"
    
    @property
    def full_name(self):
        """To'liq ism"""
        return f"{self.sname} {self.fname} {self.mname}"
    
    @property
    def passport(self):
        """Passport raqami to'liq"""
        return f"{self.ps_ser}{self.ps_num}"
    
    @property
    def is_passport_valid(self):
        """Passport amal qilish muddatini tekshirish"""
        from datetime import date
        return self.matches_date_end_document >= date.today()
    
    @property
    def is_alive(self):
        """Tirikligini tekshirish"""
        return self.livestatus == '0'
    
    def get_age(self):
        """Yoshini hisoblash"""
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    def save_from_government_data(self, data: dict):
        """Government API ma'lumotlaridan saqlash"""
        self.ps_ser = data.get('ps_ser', '')
        self.ps_num = data.get('ps_num', '')
        self.pnfl = data.get('pnfl', 0)
        self.sname = data.get('sname', '')
        self.fname = data.get('fname', '')
        self.mname = data.get('mname', '')
        self.birth_place = data.get('birth_place', '')
        self.birth_date = data.get('birth_date')
        self.birth_country = data.get('birth_country', '')
        self.birth_country_id = data.get('birth_country_id', 0)
        self.livestatus = data.get('livestatus', '0')
        self.nationality = data.get('nationality', '')
        self.nationality_id = data.get('nationality_id', 0)
        self.sex = data.get('sex', '1')
        self.doc_give_place = data.get('doc_give_place', '')
        self.doc_give_place_id = data.get('doc_give_place_id', 0)
        self.matches_date_begin_document = data.get('matches_date_begin_document')
        self.matches_date_end_document = data.get('matches_date_end_document')
        self.photo = data.get('photo', '')
        self.save()


class FaceAuthenticationLog(models.Model):
    """Face authentication urinishlari tarixi"""
    
    class AuthStatus(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Muvaffaqiyatli')
        FAILED = 'FAILED', _('Muvaffaqiyatsiz')
        NO_FACE = 'NO_FACE', _('Yuz topilmadi')
        MULTIPLE_FACES = 'MULTIPLE_FACES', _('Bir nechta yuz topildi')
        LOW_QUALITY = 'LOW_QUALITY', _('Past sifat')
        TIMEOUT = 'TIMEOUT', _('Vaqt tugadi')
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='face_auth_logs',
        verbose_name=_('Foydalanuvchi')
    )
    status = models.CharField(
        max_length=20,
        choices=AuthStatus.choices,
        verbose_name=_('Holat')
    )
    match_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Moslik darajasi')
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP manzil')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Xatolik xabari')
    )
    attempted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Urinish vaqti')
    )
    
    class Meta:
        verbose_name = _('Face Auth log')
        verbose_name_plural = _('Face Auth loglar')
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['user', '-attempted_at']),
            models.Index(fields=['status', '-attempted_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.status} - {self.attempted_at}"