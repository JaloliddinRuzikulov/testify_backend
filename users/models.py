from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model with role-based access"""
    
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', _('Super Administrator')
        ADMIN = 'ADMIN', _('Book Expert')
        QB_EXPERT = 'QB_EXPERT', _('Question Bank Expert')
        Q_EXPERT = 'Q_EXPERT', _('Question Expert')
        CREATOR = 'CREATOR', _('Q Creator')
    
    role = models.CharField(
        max_length=15,  # Increased to accommodate SUPERADMIN
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
    face_descriptor = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Face Descriptor'),
        help_text=_('Base64 encoded face descriptor for face recognition')
    )
    
    # Passport fields
    pnfl = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_('PINFL/JSHSHIR'),
        help_text=_('14-digit personal identification number')
    )
    passport = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('Passport Number'),
        help_text=_('Passport series and number (e.g., AC1987867)')
    )
    
    # Q_EXPERT subject assignment
    expert_subject = models.ForeignKey(
        'questions.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expert_users',
        verbose_name=_('Expert Subject'),
        help_text=_('Subject which this Q_EXPERT specializes in (only for Q_EXPERT role)')
    )
    
    # Role-based properties
    @property
    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.role == self.Role.SUPERADMIN
    
    @property
    def is_qb_expert(self):
        return self.role == self.Role.QB_EXPERT
    
    @property
    def is_q_expert(self):
        return self.role == self.Role.Q_EXPERT
    
    @property
    def is_expert(self):
        # Both QB and Q experts are considered experts
        return self.role in [self.Role.QB_EXPERT, self.Role.Q_EXPERT]
    
    @property
    def is_creator(self):
        return self.role == self.Role.CREATOR
    
    @property
    def can_manage_questions(self):
        # Q Expert, QB Expert and higher can manage questions
        return self.role in [self.Role.SUPERADMIN, self.Role.ADMIN, self.Role.QB_EXPERT, self.Role.Q_EXPERT]
    
    @property
    def can_manage_banks(self):
        # Only QB Expert and higher can manage question banks
        return self.role in [self.Role.SUPERADMIN, self.Role.ADMIN, self.Role.QB_EXPERT]
    
    @property
    def can_manage_users(self):
        # Only Admin and SuperAdmin can manage users
        return self.role in [self.Role.SUPERADMIN, self.Role.ADMIN]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')