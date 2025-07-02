from django.contrib import admin
from .models import Subject, Topic, Question, QuestionOption


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
    list_display = ('name', 'subject')
    list_filter = ('subject',)
    search_fields = ('name', 'subject__name')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin for Question model"""
    list_display = ('id', 'subject', 'topic', 'difficulty', 'status', 'created_by', 'created_at')
    list_filter = ('subject', 'topic', 'difficulty', 'status', 'created_at')
    search_fields = ('text', 'subject__name', 'topic__name')
    readonly_fields = ('created_by', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    inlines = [QuestionOptionInline]
    
    def save_model(self, request, obj, form, change):
        """Set created_by on new questions"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)