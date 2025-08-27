from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()


class QuestionBank(models.Model):
    """Savollar banki - ekspertlar tomonidan yaratiladi"""
    
    STATUS_CHOICES = (
        ('draft', 'Qoralama'),
        ('active', 'Faol'),
        ('archived', 'Arxivlangan'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Bank nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    subject = models.ForeignKey(
        'questions.Subject', 
        on_delete=models.CASCADE,
        null=True,  # Keep nullable for backward compatibility
        blank=False,  # But required in forms
        related_name='question_banks',
        verbose_name="Fan"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Holat"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Savollar banki"
        verbose_name_plural = "Savollar banklari"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.subject:
            return f"{self.name} ({self.subject.name})"
        return self.name
    
    @property
    def questions_count(self):
        """Bankdagi savollar soni (faqat tasdiqlangan)"""
        from questions.models import Question
        # Only count approved questions
        return self.bank_questions.filter(
            question__status='APPROVED'
        ).count()
    
    @property
    def total_questions_count(self):
        """Bankdagi barcha savollar soni (status qat'iy nazar)"""
        return self.bank_questions.count()
    
    @property
    def approved_questions_count(self):
        """Bankdagi tasdiqlangan savollar soni"""
        return self.bank_questions.filter(
            question__status='APPROVED'
        ).count()
    
    @property
    def pending_questions_count(self):
        """Bankdagi kutilayotgan savollar soni"""
        return self.bank_questions.filter(
            question__status='PENDING'
        ).count()
    
    @property
    def rejected_questions_count(self):
        """Bankdagi rad etilgan savollar soni"""
        return self.bank_questions.filter(
            question__status='REJECTED'
        ).count()
    
    @property
    def difficulty_distribution(self):
        """Qiyinlik bo'yicha taqsimot (faqat tasdiqlangan savollar)"""
        from django.db.models import Count
        from questions.models import Question
        
        # Get all approved questions in this bank through BankQuestion
        question_ids = self.bank_questions.filter(
            question__status='APPROVED'
        ).values_list('question_id', flat=True)
        
        # Get difficulty distribution from Question model
        distribution = Question.objects.filter(
            id__in=question_ids
        ).values('difficulty').annotate(
            count=Count('id')
        ).order_by('difficulty')
        
        result = {'easy': 0, 'medium': 0, 'hard': 0}
        
        for item in distribution:
            if item['difficulty']:
                level = item['difficulty'].lower()
                if level in result:
                    result[level] = item['count']
        
        return result
    
    @property
    def target_questions_count(self):
        """Jami nechta savol kerak"""
        return self.topic_quotas.aggregate(total=models.Sum('target_count'))['total'] or 0
    
    @property
    def current_questions_count(self):
        """Hozirda nechta savol kiritilgan"""
        return self.topic_quotas.aggregate(total=models.Sum('current_count'))['total'] or 0
    
    @property
    def remaining_questions_count(self):
        """Nechta savol qolgan"""
        return max(0, self.target_questions_count - self.current_questions_count)
    
    @property
    def overall_progress(self):
        """Umumiy progress foizda"""
        if self.target_questions_count == 0:
            return 100
        return min(100, round((self.current_questions_count / self.target_questions_count) * 100))
    
    @property
    def is_completed(self):
        """To'plam to'liq yig'ildimi"""
        return self.current_questions_count >= self.target_questions_count
    
    @property
    def completion_status(self):
        """To'plam holati"""
        if self.is_completed:
            return "Completed"
        elif self.current_questions_count > 0:
            return "In Progress"
        else:
            return "Not Started"


class BankTopicQuota(models.Model):
    """Question Bank uchun topic-level kvotalar"""
    
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name='topic_quotas',
        verbose_name="Savol to'plami"
    )
    topic = models.ForeignKey(
        'questions.Topic',
        on_delete=models.CASCADE,
        verbose_name="Mavzu"
    )
    section = models.ForeignKey(
        'questions.Section',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Bo'lim"
    )
    difficulty = models.ForeignKey(
        'questions.Difficulty',
        on_delete=models.CASCADE,
        verbose_name="Qiyinlik darajasi"
    )
    target_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Kerakli savollar soni"
    )
    current_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name="Hozirgi savollar soni"
    )
    
    @property
    def remaining_count(self):
        """Qolgan savollar soni"""
        return max(0, self.target_count - self.current_count)
    
    @property
    def progress_percentage(self):
        """Progress foizda"""
        if self.target_count == 0:
            return 100
        return min(100, round((self.current_count / self.target_count) * 100))
    
    @property
    def is_completed(self):
        """Kvota bajarilganmi?"""
        return self.current_count >= self.target_count
    
    class Meta:
        verbose_name = "Mavzu kvotasi"
        verbose_name_plural = "Mavzu kvotalari"
        unique_together = ['bank', 'topic', 'section', 'difficulty']
        ordering = ['topic__number', 'difficulty__level']
    
    def __str__(self):
        section_part = f" - {self.section.name}" if self.section else ""
        return f"{self.topic.name}{section_part} ({self.difficulty.name}): {self.current_count}/{self.target_count}"


class BankQuestion(models.Model):
    """Bankdagi savollar"""
    
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name='bank_questions',
        verbose_name="Bank"
    )
    question = models.ForeignKey(
        'questions.Question',
        on_delete=models.CASCADE,
        verbose_name="Savol"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Qo'shgan"
    )
    
    class Meta:
        verbose_name = "Bank savoli"
        verbose_name_plural = "Bank savollari"
        unique_together = ['bank', 'question']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.bank.name} - {self.question.text[:50]}"


class OrderPointDistribution(models.Model):
    """Buyurtmadagi har bir punkt bo'yicha savollar taqsimoti"""
    
    order = models.ForeignKey(
        'BankOrder',
        on_delete=models.CASCADE,
        related_name='point_distributions',
        verbose_name="Buyurtma"
    )
    topic = models.ForeignKey(
        'questions.Topic',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Topic"
    )
    section = models.ForeignKey(
        'questions.Section',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Section"
    )
    questions_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Savollar soni"
    )
    difficulty_level = models.CharField(
        max_length=10,
        choices=[
            ('EASY', 'Oson'),
            ('MEDIUM', "O'rta"),
            ('HARD', 'Qiyin'),
        ],
        default='MEDIUM',
        verbose_name="Qiyinlik darajasi"
    )
    
    class Meta:
        verbose_name = "Topic distribution"
        verbose_name_plural = "Topic distributions"
        unique_together = [['order', 'topic', 'section', 'difficulty_level']]
    
    def __str__(self):
        section_name = f" -> {self.section.name}" if self.section else ""
        return f"{self.topic.name}{section_name}: {self.questions_count} ta ({self.get_difficulty_level_display()})"


class BankOrder(models.Model):
    """Admin tomonidan ekspertga beriladigan buyurtmalar"""
    
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('processing', 'Jarayonda'),
        ('completed', 'Bajarildi'),
        ('cancelled', 'Bekor qilindi'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Bank"
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_orders',
        limit_choices_to={'role': 'ADMIN'},
        verbose_name="Admin"
    )
    total_questions = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name="Jami savollar"
    )
    easy_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Oson savollar"
    )
    medium_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="O'rta savollar"
    )
    hard_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Qiyin savollar"
    )
    deadline = models.DateTimeField(verbose_name="Muddat")
    notes = models.TextField(blank=True, verbose_name="Izohlar")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Holat"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Bank buyurtmasi"
        verbose_name_plural = "Bank buyurtmalari"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Buyurtma #{self.id} - {self.bank.name}"
    
    def complete(self):
        """Buyurtmani yakunlash"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class TestBook(models.Model):
    """Test kitobi - bankdan savollar olib variantlar yaratiladi"""
    
    STATUS_CHOICES = (
        ('draft', 'Qoralama'),
        ('published', 'Nashr etilgan'),
        ('archived', 'Arxivlangan'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name="Kitob nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        related_name='test_books',
        verbose_name="Savollar banki"
    )
    variants_count = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Variantlar soni"
    )
    questions_per_variant = models.IntegerField(
        default=30,
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name="Har variantdagi savollar"
    )
    time_limit = models.IntegerField(
        default=180,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        verbose_name="Vaqt limiti (daqiqa)"
    )
    passing_score = models.IntegerField(
        default=60,
        validators=[MinValueValidator(40), MaxValueValidator(100)],
        verbose_name="O'tish balli (%)"
    )
    
    # Difficulty mix
    easy_percentage = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Oson savollar %"
    )
    medium_percentage = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="O'rta savollar %"
    )
    hard_percentage = models.IntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Qiyin savollar %"
    )
    
    # Settings
    shuffle_questions = models.BooleanField(default=True, verbose_name="Savollarni aralashtirish")
    shuffle_options = models.BooleanField(default=True, verbose_name="Javoblarni aralashtirish")
    show_results = models.BooleanField(default=True, verbose_name="Natijalarni ko'rsatish")
    allow_review = models.BooleanField(default=False, verbose_name="Tekshirishga ruxsat")
    require_auth = models.BooleanField(default=True, verbose_name="Autentifikatsiya talab qilish")
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Holat"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_books',
        verbose_name="Yaratgan"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Stats
    total_attempts = models.IntegerField(default=0, verbose_name="Jami urinishlar")
    total_score = models.FloatField(default=0, verbose_name="Jami ball")
    
    # Share
    share_link = models.URLField(blank=True, verbose_name="Ulashish havolasi")
    qr_code = models.TextField(blank=True, verbose_name="QR kod")
    
    class Meta:
        verbose_name = "Test kitobi"
        verbose_name_plural = "Test kitoblari"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def average_score(self):
        """O'rtacha ball"""
        if self.total_attempts > 0:
            return self.total_score / self.total_attempts
        return 0
    
    @property
    def pass_rate(self):
        """O'tish foizi"""
        if self.total_attempts > 0:
            passed = self.attempts.filter(score__gte=self.passing_score).count()
            return (passed / self.total_attempts) * 100
        return 0
    
    def publish(self):
        """Kitobni nashr etish"""
        self.status = 'published'
        self.published_at = timezone.now()
        # Generate share link and QR code
        self.share_link = f"https://test.uz/book/{self.id}"
        self.save()
        # Generate variants
        self.generate_variants()
    
    def generate_variants(self):
        """Variantlar generatsiya qilish"""
        from random import sample, shuffle
        
        # Get questions from bank
        bank_questions = list(self.bank.questions.filter(
            question__status='APPROVED'
        ).select_related('question'))
        
        if len(bank_questions) < self.questions_per_variant:
            raise ValueError("Bankda yetarli savol yo'q")
        
        # Calculate question counts by difficulty
        easy_count = int(self.questions_per_variant * self.easy_percentage / 100)
        medium_count = int(self.questions_per_variant * self.medium_percentage / 100)
        hard_count = self.questions_per_variant - easy_count - medium_count
        
        # Filter questions by difficulty
        easy_questions = [q for q in bank_questions if q.question.difficulty_level == 'EASY']
        medium_questions = [q for q in bank_questions if q.question.difficulty_level == 'MEDIUM']
        hard_questions = [q for q in bank_questions if q.question.difficulty_level == 'HARD']
        
        # Generate variants
        for variant_num in range(1, self.variants_count + 1):
            variant = TestVariant.objects.create(
                book=self,
                variant_number=variant_num
            )
            
            # Select questions for this variant
            selected_questions = []
            
            if len(easy_questions) >= easy_count:
                selected_questions.extend(sample(easy_questions, easy_count))
            if len(medium_questions) >= medium_count:
                selected_questions.extend(sample(medium_questions, medium_count))
            if len(hard_questions) >= hard_count:
                selected_questions.extend(sample(hard_questions, hard_count))
            
            # Fill remaining if needed
            remaining = self.questions_per_variant - len(selected_questions)
            if remaining > 0:
                available = [q for q in bank_questions if q not in selected_questions]
                selected_questions.extend(sample(available, min(remaining, len(available))))
            
            # Shuffle if needed
            if self.shuffle_questions:
                shuffle(selected_questions)
            
            # Create variant questions
            for order, bank_q in enumerate(selected_questions, 1):
                VariantQuestion.objects.create(
                    variant=variant,
                    question=bank_q.question,
                    order=order
                )


class TestVariant(models.Model):
    """Test kitobi varianti"""
    
    book = models.ForeignKey(
        TestBook,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name="Kitob"
    )
    variant_number = models.IntegerField(verbose_name="Variant raqami")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Test varianti"
        verbose_name_plural = "Test variantlari"
        unique_together = ['book', 'variant_number']
        ordering = ['variant_number']
    
    def __str__(self):
        return f"{self.book.title} - Variant {self.variant_number}"


class VariantQuestion(models.Model):
    """Variantdagi savollar"""
    
    variant = models.ForeignKey(
        TestVariant,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Variant"
    )
    question = models.ForeignKey(
        'questions.Question',
        on_delete=models.CASCADE,
        verbose_name="Savol"
    )
    order = models.IntegerField(verbose_name="Tartib")
    
    class Meta:
        verbose_name = "Variant savoli"
        verbose_name_plural = "Variant savollari"
        unique_together = ['variant', 'question']
        ordering = ['order']
    
    def __str__(self):
        return f"V{self.variant.variant_number} - Q{self.order}"


class TestAttempt(models.Model):
    """Test urinishi"""
    
    book = models.ForeignKey(
        TestBook,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name="Kitob"
    )
    variant = models.ForeignKey(
        TestVariant,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name="Variant"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='test_attempts',
        verbose_name="Foydalanuvchi"
    )
    score = models.FloatField(default=0, verbose_name="Ball")
    correct_answers = models.IntegerField(default=0, verbose_name="To'g'ri javoblar")
    wrong_answers = models.IntegerField(default=0, verbose_name="Noto'g'ri javoblar")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.IntegerField(default=0, verbose_name="Sarflangan vaqt (soniya)")
    
    class Meta:
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user} - {self.book.title} - {self.score}%"
    
    def calculate_score(self):
        """Ballni hisoblash"""
        if self.variant.questions.count() > 0:
            self.score = (self.correct_answers / self.variant.questions.count()) * 100
            self.save()
            
            # Update book stats
            self.book.total_attempts += 1
            self.book.total_score += self.score
            self.book.save()