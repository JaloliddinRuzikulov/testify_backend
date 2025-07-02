from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model with role-based access"""
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        EXPERT = 'EXPERT', _('Expert')
        CREATOR = 'CREATOR', _('Question Creator')
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CREATOR,
        verbose_name=_('User Role')
    )
    
    # Additional fields
    bio = models.TextField(blank=True, verbose_name=_('Biography'))
    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
        verbose_name=_('Profile Image')
    )
    
    # Role-based properties
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_expert(self):
        return self.role == self.Role.EXPERT
    
    @property
    def is_creator(self):
        return self.role == self.Role.CREATOR
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')