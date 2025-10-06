from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Subject(models.Model):
    """Subject model for categorizing questions"""
    name = models.CharField(max_length=100, verbose_name=_('Subject Name'))
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Subject Code'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        ordering = ['name']


class Topic(models.Model):
    """Topic model for main topics within subjects"""
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics',
        verbose_name=_('Subject')
    )
    name = models.CharField(max_length=300, verbose_name=_('Topic Name'))
    number = models.PositiveIntegerField(verbose_name=_('Topic Number'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    
    def __str__(self):
        return f"{self.number}. {self.name} ({self.subject.name})"
    
    class Meta:
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')
        ordering = ['subject__name', 'number']
        unique_together = ['subject', 'number']


class Section(models.Model):
    """Section model for sub-sections within topics"""
    topic = models.ForeignKey(
        Topic, 
        on_delete=models.CASCADE, 
        related_name='sections',
        verbose_name=_('Topic')
    )
    name = models.CharField(max_length=200, verbose_name=_('Section Name'))
    number = models.PositiveIntegerField(verbose_name=_('Section Number'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    
    def __str__(self):
        return f"{self.topic.number}.{self.number}. {self.name} ({self.topic.subject.name})"
    
    class Meta:
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        ordering = ['topic__subject__name', 'topic__number', 'number']
        unique_together = ['topic', 'number']


class Difficulty(models.Model):
    """Dynamic difficulty levels for questions"""
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Difficulty Name'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('Difficulty Code'))
    level = models.PositiveIntegerField(unique=True, verbose_name=_('Difficulty Level'), 
                                        help_text=_('Lower number = easier'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Difficulty')
        verbose_name_plural = _('Difficulties')
        ordering = ['level']


# Keep for backward compatibility temporarily
class DifficultyLevel(models.TextChoices):
    """Difficulty levels for questions - DEPRECATED"""
    EASY = 'EASY', _('Easy')
    MEDIUM = 'MEDIUM', _('Medium')
    HARD = 'HARD', _('Hard')


class QuestionType(models.TextChoices):
    """Question type options"""
    SINGLE = 'SINGLE', _('Single Choice')
    MULTIPLE = 'MULTIPLE', _('Multiple Choice')
    READING = 'READING', _('Reading Comprehension')


class QuestionStatus(models.TextChoices):
    """Status options for questions"""
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted for Review')
    PENDING = 'PENDING', _('Pending Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    ARCHIVED = 'ARCHIVED', _('Archived')


class Question(models.Model):
    """Question model with LaTeX support"""
    
    # Basic fields - NEW HIERARCHY: Subject > Topic > Section
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name=_('Subject')
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name=_('Topic')
    )
    section = models.ForeignKey(
        Section, 
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Section'),
        null=True,
        blank=True
    )
    # Question type field
    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.SINGLE,
        verbose_name=_('Question Type')
    )

    # Reading comprehension fields
    reading_text = models.TextField(
        blank=True,
        verbose_name=_('Reading Text'),
        help_text=_('Main reading text for comprehension questions')
    )
    parent_question = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_questions',
        verbose_name=_('Parent Question'),
        help_text=_('Parent question for reading comprehension sub-questions')
    )
    question_order = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Question Order'),
        help_text=_('Order of sub-questions in reading comprehension')
    )

    # Keep old field for backward compatibility
    difficulty = models.CharField(
        max_length=10,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM,
        verbose_name=_('Difficulty Level (OLD)'),
        help_text=_('DEPRECATED - Use difficulty_level instead')
    )

    # New dynamic difficulty field
    difficulty_level = models.ForeignKey(
        Difficulty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name=_('Difficulty Level')
    )

    # Content fields (with LaTeX support)
    text = models.TextField(verbose_name=_('Question Text in LaTeX'))
    additional_text = models.TextField(blank=True, verbose_name=_('Additional Information in LaTeX'))
    
    # Images or attachments
    image = models.ImageField(
        upload_to='question_images/',
        blank=True, 
        null=True,
        verbose_name=_('Question Image')
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_questions',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    # Review
    status = models.CharField(
        max_length=10,
        choices=QuestionStatus.choices,
        default=QuestionStatus.DRAFT,
        verbose_name=_('Status')
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_questions',
        verbose_name=_('Reviewed By')
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Reviewed At'))
    review_comment = models.TextField(blank=True, verbose_name=_('Review Comment'))
    
    def __str__(self):
        if self.subject:
            return f"Question #{self.id} ({self.subject.name})"
        return f"Question #{self.id} (No Subject)"
    
    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ['-created_at']


class QuestionOption(models.Model):
    """Model for question options/answers with LaTeX support"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name=_('Question')
    )
    text = models.TextField(verbose_name=_('Option Text in LaTeX'))
    is_correct = models.BooleanField(default=False, verbose_name=_('Is Correct Answer'))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_('Display Order'))
    
    def __str__(self):
        return f"Option for Question #{self.question.id} - {'Correct' if self.is_correct else 'Incorrect'}"
    
    class Meta:
        verbose_name = _('Question Option')
        verbose_name_plural = _('Question Options')
        ordering = ['question', 'order']
        unique_together = ['question', 'order']