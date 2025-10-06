from django.contrib import admin
from .models import Subject, Topic, Section, Question, QuestionOption, Difficulty


@admin.register(Difficulty)
class DifficultyAdmin(admin.ModelAdmin):
    """Admin for Difficulty model"""
    list_display = ('name', 'code', 'level', 'is_active', 'questions_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('level',)
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = 'Questions'


class QuestionOptionInline(admin.TabularInline):
    """Inline admin for question options"""
    model = QuestionOption
    extra = 4
    min_num = 2


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin for Subject model"""
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Admin for Topic model"""
    list_display = ('number', 'name', 'subject')
    list_filter = ('subject',)
    search_fields = ('name', 'subject__name')
    ordering = ('subject__name', 'number')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    """Admin for Section model"""
    list_display = ('number', 'name', 'topic', 'get_subject')
    list_filter = ('topic__subject', 'topic')
    search_fields = ('name', 'topic__name', 'topic__subject__name')
    ordering = ('topic__subject__name', 'topic__number', 'number')
    
    def get_subject(self, obj):
        return obj.topic.subject.name
    get_subject.short_description = 'Subject'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin for Question model"""
    list_display = ('id', 'subject', 'topic', 'section', 'difficulty', 'status', 'created_by', 'created_at')
    list_filter = ('subject', 'topic', 'section', 'difficulty', 'status', 'question_type', 'created_at')
    search_fields = ('text', 'reading_text', 'additional_text', 'subject__name', 'topic__name', 'section__name')
    readonly_fields = ('created_by', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    inlines = [QuestionOptionInline]

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('subject', 'topic', 'section', 'difficulty', 'difficulty_level', 'status')
        }),
        ('Savol turi va tarkibi', {
            'fields': ('question_type', 'text', 'additional_text', 'image'),
        }),
        ('Reading Comprehension (faqat READING turi uchun)', {
            'fields': ('reading_text', 'parent_question', 'question_order'),
            'classes': ('collapse',),
            'description': 'Bu maydonlar faqat Reading Comprehension turidagi savollar uchun ishlatiladi'
        }),
        ('Ko\'rib chiqish ma\'lumotlari', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_comment'),
            'classes': ('collapse',)
        }),
        ('Tizim ma\'lumotlari', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Set created_by on new questions"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)