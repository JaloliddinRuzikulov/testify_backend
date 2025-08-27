from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    QuestionBank, BankQuestion, BankOrder, OrderPointDistribution,
    TestBook, TestVariant, VariantQuestion, TestAttempt, BankTopicQuota
)


@admin.register(BankTopicQuota)
class BankTopicQuotaAdmin(admin.ModelAdmin):
    list_display = [
        'bank', 'topic', 'section', 'difficulty', 
        'target_count', 'current_count', 'remaining_count_display', 
        'progress_display', 'is_completed'
    ]
    list_filter = ['bank', 'topic__subject', 'difficulty']
    search_fields = ['bank__name', 'topic__name', 'section__name']
    readonly_fields = ['current_count', 'remaining_count_display', 'progress_display']
    
    def remaining_count_display(self, obj):
        """Display remaining count"""
        remaining = obj.remaining_count
        color = 'green' if remaining == 0 else 'orange'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, remaining
        )
    remaining_count_display.short_description = 'Qolgan'
    
    def progress_display(self, obj):
        """Display progress bar"""
        progress = obj.progress_percentage
        color = 'green' if progress == 100 else 'blue'
        return format_html(
            '<div style="width:100px;background:#ddd;border-radius:4px;">'
            '<div style="width:{}%;background:{};height:20px;border-radius:4px;"></div>'
            '</div> <span>{}%</span>',
            progress, color, progress
        )
    progress_display.short_description = 'Progress'
    
    def is_completed(self, obj):
        """Check if quota is completed"""
        return obj.is_completed
    is_completed.boolean = True
    is_completed.short_description = 'Tugallangan'


@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'subject', 'status', 'approved_count_display', 
        'pending_count_display', 'created_at'
    ]
    list_filter = ['status', 'subject', 'created_at']
    search_fields = ['name', 'subject__name']
    readonly_fields = [
        'id', 'approved_count_display', 'pending_count_display', 
        'rejected_count_display', 'difficulty_stats', 'created_at', 'updated_at'
    ]
    fieldsets = [
        ('Asosiy ma\'lumotlar', {
            'fields': ['name', 'description', 'subject', 'status']
        }),
        ('Statistika', {
            'fields': [
                'approved_count_display', 'pending_count_display',
                'rejected_count_display', 'difficulty_stats'
            ],
            'classes': ['collapse']
        }),
        ('Vaqt belgilari', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def approved_count_display(self, obj):
        count = obj.approved_questions_count
        return format_html(
            '<span style="color: green; font-weight: bold;">{}</span>', 
            count
        )
    approved_count_display.short_description = 'Tasdiqlangan'
    
    def pending_count_display(self, obj):
        count = obj.pending_questions_count
        if count > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{}</span>', 
                count
            )
        return count
    pending_count_display.short_description = 'Kutilmoqda'
    
    def rejected_count_display(self, obj):
        count = obj.rejected_questions_count
        if count > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>', 
                count
            )
        return count
    rejected_count_display.short_description = 'Rad etilgan'
    
    def difficulty_stats(self, obj):
        dist = obj.difficulty_distribution
        return format_html(
            '<div style="font-size: 12px;">'
            '<span style="color: green;">Oson: {}</span> | '
            '<span style="color: orange;">O\'rta: {}</span> | '
            '<span style="color: red;">Qiyin: {}</span>'
            '</div>',
            dist['easy'], dist['medium'], dist['hard']
        )
    difficulty_stats.short_description = 'Qiyinlik taqsimoti'


@admin.register(BankQuestion)
class BankQuestionAdmin(admin.ModelAdmin):
    list_display = ['bank', 'question_preview', 'question_status', 'added_by', 'added_at']
    list_filter = ['bank', 'question__status', 'added_at']
    search_fields = ['bank__name', 'question__text', 'question__fan__name']
    readonly_fields = ['added_at']
    
    def question_preview(self, obj):
        text = obj.question.text[:50] + "..." if len(obj.question.text) > 50 else obj.question.text
        return text
    question_preview.short_description = 'Savol matni'
    
    def question_status(self, obj):
        status = obj.question.status
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green', 
            'REJECTED': 'red',
            'ARCHIVED': 'gray'
        }
        color = colors.get(status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', 
            color, obj.question.get_status_display()
        )
    question_status.short_description = 'Holat'


class OrderPointDistributionInline(admin.TabularInline):
    model = OrderPointDistribution
    extra = 0
    fields = ['topic', 'section', 'questions_count', 'difficulty_level']


@admin.register(BankOrder)
class BankOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'bank', 'admin', 'status', 'total_questions', 
        'difficulty_summary', 'deadline', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'deadline']
    search_fields = ['bank__name', 'admin__first_name', 'admin__last_name', 'notes']
    readonly_fields = ['id', 'created_at', 'completed_at', 'points_summary']
    inlines = [OrderPointDistributionInline]
    
    fieldsets = [
        ('Asosiy ma\'lumotlar', {
            'fields': ['bank', 'admin', 'status', 'deadline', 'notes']
        }),
        ('Savollar taqsimoti', {
            'fields': [
                'total_questions', 'easy_count', 'medium_count', 'hard_count'
            ]
        }),
        ('Punktlar bo\'yicha taqsimot', {
            'fields': ['points_summary'],
            'classes': ['collapse']
        }),
        ('Vaqt belgilari', {
            'fields': ['created_at', 'completed_at'],
            'classes': ['collapse']
        }),
    ]
    
    def order_id(self, obj):
        return str(obj.id)[:8] + "..."
    order_id.short_description = 'ID'
    
    def difficulty_summary(self, obj):
        return format_html(
            '<span style="color: green;">O: {}</span> | '
            '<span style="color: orange;">O\': {}</span> | '
            '<span style="color: red;">Q: {}</span>',
            obj.easy_count, obj.medium_count, obj.hard_count
        )
    difficulty_summary.short_description = 'Qiyinlik'
    
    def points_summary(self, obj):
        distributions = obj.point_distributions.all()
        if not distributions:
            return "Section bo'yicha taqsimot yo'q"
        
        html = "<ul style='margin: 0; padding-left: 15px;'>"
        for dist in distributions:
            if dist.section and dist.topic:
                html += f"<li><strong>{dist.section.name}</strong> ({dist.topic.name}): {dist.questions_count} ta - {dist.get_difficulty_level_display()}</li>"
        html += "</ul>"
        
        return mark_safe(html)
    points_summary.short_description = 'Section bo\'yicha taqsimot'


@admin.register(OrderPointDistribution)
class OrderPointDistributionAdmin(admin.ModelAdmin):
    list_display = ['order_preview', 'topic', 'section', 'questions_count', 'difficulty_level']
    list_filter = ['difficulty_level', 'topic', 'order__status']
    search_fields = ['topic__name', 'section__name', 'order__bank__name']
    
    def order_preview(self, obj):
        return f"#{str(obj.order.id)[:8]}... - {obj.order.bank.name}"
    order_preview.short_description = 'Buyurtma'


class TestVariantInline(admin.TabularInline):
    model = TestVariant
    extra = 0
    readonly_fields = ['created_at', 'questions_count']
    fields = ['variant_number', 'questions_count', 'created_at']
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Savollar soni'


@admin.register(TestBook)
class TestBookAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'bank', 'status', 'variants_count', 'questions_per_variant',
        'total_attempts', 'average_score_display', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'bank', 'created_at', 'require_auth']
    search_fields = ['title', 'bank__name', 'created_by__first_name']
    readonly_fields = [
        'id', 'share_link', 'qr_code', 'total_attempts', 'total_score',
        'average_score_display', 'pass_rate_display', 'created_at', 'published_at'
    ]
    inlines = [TestVariantInline]
    actions = ['publish_books']
    
    fieldsets = [
        ('Asosiy ma\'lumotlar', {
            'fields': ['title', 'description', 'bank', 'status']
        }),
        ('Test sozlamalari', {
            'fields': [
                'variants_count', 'questions_per_variant', 'time_limit', 'passing_score'
            ]
        }),
        ('Qiyinlik taqsimoti (%)', {
            'fields': ['easy_percentage', 'medium_percentage', 'hard_percentage']
        }),
        ('Qo\'shimcha sozlamalar', {
            'fields': [
                'shuffle_questions', 'shuffle_options', 'show_results', 
                'allow_review', 'require_auth'
            ]
        }),
        ('Statistika', {
            'fields': [
                'total_attempts', 'average_score_display', 'pass_rate_display'
            ],
            'classes': ['collapse']
        }),
        ('Ulashish', {
            'fields': ['share_link', 'qr_code'],
            'classes': ['collapse']
        }),
        ('Vaqt belgilari', {
            'fields': ['created_by', 'created_at', 'published_at'],
            'classes': ['collapse']
        }),
    ]
    
    def average_score_display(self, obj):
        avg = obj.average_score
        if avg > 0:
            color = 'green' if avg >= 70 else 'orange' if avg >= 50 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>', 
                color, avg
            )
        return "0%"
    average_score_display.short_description = 'O\'rtacha ball'
    
    def pass_rate_display(self, obj):
        rate = obj.pass_rate
        if rate > 0:
            color = 'green' if rate >= 70 else 'orange' if rate >= 50 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>', 
                color, rate
            )
        return "0%"
    pass_rate_display.short_description = 'O\'tish foizi'
    
    def publish_books(self, request, queryset):
        for book in queryset.filter(status='draft'):
            try:
                book.publish()
                self.message_user(request, f"{book.title} nashr etildi")
            except Exception as e:
                self.message_user(request, f"{book.title}: {str(e)}", level='ERROR')
    
    publish_books.short_description = "Tanlangan kitoblarni nashr etish"


@admin.register(TestVariant)
class TestVariantAdmin(admin.ModelAdmin):
    list_display = ['variant_display', 'book', 'questions_count', 'attempts_count', 'created_at']
    list_filter = ['book', 'created_at']
    search_fields = ['book__title', 'book__bank__name']
    readonly_fields = ['created_at', 'questions_count', 'attempts_count']
    
    def variant_display(self, obj):
        return f"Variant {obj.variant_number}"
    variant_display.short_description = 'Variant'
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Savollar soni'
    
    def attempts_count(self, obj):
        return obj.attempts.count()
    attempts_count.short_description = 'Urinishlar'


@admin.register(VariantQuestion)
class VariantQuestionAdmin(admin.ModelAdmin):
    list_display = ['variant_display', 'order', 'question_preview', 'question_difficulty']
    list_filter = ['variant__book', 'question__difficulty', 'variant__variant_number']
    search_fields = ['question__text', 'variant__book__title']
    ordering = ['variant', 'order']
    
    def variant_display(self, obj):
        return f"{obj.variant.book.title} - V{obj.variant.variant_number}"
    variant_display.short_description = 'Variant'
    
    def question_preview(self, obj):
        text = obj.question.text[:50] + "..." if len(obj.question.text) > 50 else obj.question.text
        return text
    question_preview.short_description = 'Savol'
    
    def question_difficulty(self, obj):
        diff = obj.question.difficulty
        colors = {'easy': 'green', 'medium': 'orange', 'hard': 'red'}
        color = colors.get(diff.lower() if diff else 'medium', 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', 
            color, diff.title() if diff else 'Medium'
        )
    question_difficulty.short_description = 'Qiyinlik'


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'book_title', 'variant_display', 'score_display', 
        'correct_answers', 'time_spent_display', 'started_at', 'completion_status'
    ]
    list_filter = ['book', 'completed_at', 'started_at']
    search_fields = ['user__first_name', 'user__last_name', 'book__title']
    readonly_fields = ['started_at', 'score_display', 'time_spent_display', 'completion_status']
    
    fieldsets = [
        ('Asosiy ma\'lumotlar', {
            'fields': ['user', 'book', 'variant']
        }),
        ('Natijalar', {
            'fields': ['score_display', 'correct_answers', 'wrong_answers', 'completion_status']
        }),
        ('Vaqt', {
            'fields': ['started_at', 'completed_at', 'time_spent_display']
        }),
    ]
    
    def book_title(self, obj):
        return obj.book.title
    book_title.short_description = 'Kitob'
    
    def variant_display(self, obj):
        return f"V{obj.variant.variant_number}"
    variant_display.short_description = 'Variant'
    
    def score_display(self, obj):
        score = obj.score
        if score >= 70:
            color = 'green'
        elif score >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>', 
            color, score
        )
    score_display.short_description = 'Ball'
    
    def time_spent_display(self, obj):
        if obj.time_spent > 0:
            minutes = obj.time_spent // 60
            seconds = obj.time_spent % 60
            return f"{minutes}:{seconds:02d}"
        return "0:00"
    time_spent_display.short_description = 'Vaqt'
    
    def completion_status(self, obj):
        if obj.completed_at:
            return format_html('<span style="color: green;">✓ Tugallangan</span>')
        else:
            return format_html('<span style="color: red;">⏳ Jarayonda</span>')
    completion_status.short_description = 'Holat'


# Admin site customization
admin.site.site_header = "DTM Test Platform Admin"
admin.site.site_title = "DTM Admin"
admin.site.index_title = "Savollar banki boshqaruvi"