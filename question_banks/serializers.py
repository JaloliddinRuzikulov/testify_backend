from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    QuestionBank, BankQuestion, BankOrder, OrderPointDistribution,
    TestBook, TestVariant, VariantQuestion, TestAttempt, BankTopicQuota
)
from questions.models import Question, Subject, Topic, Section, Difficulty
from questions.serializers import QuestionDetailSerializer, SubjectSerializer, TopicSerializer, SectionSerializer, DifficultySerializer
from users.serializers import UserSerializer

User = get_user_model()


class BankTopicQuotaSerializer(serializers.ModelSerializer):
    bank = serializers.PrimaryKeyRelatedField(
        queryset=QuestionBank.objects.all(),
        required=True
    )
    topic = TopicSerializer(read_only=True)
    section = SectionSerializer(read_only=True)
    difficulty = DifficultySerializer(read_only=True)
    
    topic_id = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(),
        source='topic',
        write_only=True
    )
    section_id = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(),
        source='section',
        write_only=True,
        required=False,
        allow_null=True
    )
    difficulty_id = serializers.PrimaryKeyRelatedField(
        queryset=Difficulty.objects.filter(is_active=True),
        source='difficulty',
        write_only=True
    )
    
    # Read-only properties
    remaining_count = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = BankTopicQuota
        fields = [
            'id', 'bank', 'topic', 'topic_id', 'section', 'section_id',
            'difficulty', 'difficulty_id', 'target_count', 'current_count',
            'remaining_count', 'progress_percentage', 'is_completed'
        ]
        read_only_fields = ['current_count']


class BankQuestionSerializer(serializers.ModelSerializer):
    question = QuestionDetailSerializer(read_only=True)
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.filter(status='APPROVED'),
        source='question',
        write_only=True
    )
    
    class Meta:
        model = BankQuestion
        fields = ['id', 'question', 'question_id', 'added_at', 'added_by']
        read_only_fields = ['added_at', 'added_by']


class QuestionBankSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True,
        required=True  # Subject is now required
    )
    questions_count = serializers.IntegerField(read_only=True)
    total_questions_count = serializers.IntegerField(read_only=True)
    approved_questions_count = serializers.IntegerField(read_only=True)
    pending_questions_count = serializers.IntegerField(read_only=True)
    rejected_questions_count = serializers.IntegerField(read_only=True)
    difficulty_distribution = serializers.DictField(read_only=True)
    
    # New quota-related fields
    topic_quotas = BankTopicQuotaSerializer(many=True, read_only=True)
    target_questions_count = serializers.IntegerField(read_only=True)
    current_questions_count = serializers.IntegerField(read_only=True)
    remaining_questions_count = serializers.IntegerField(read_only=True)
    overall_progress = serializers.IntegerField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    completion_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = QuestionBank
        fields = [
            'id', 'name', 'description', 'subject', 'subject_id',
            'status', 'questions_count',
            'total_questions_count', 'approved_questions_count', 
            'pending_questions_count', 'rejected_questions_count',
            'difficulty_distribution', 'topic_quotas',
            'target_questions_count', 'current_questions_count',
            'remaining_questions_count', 'overall_progress',
            'is_completed', 'completion_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class QuestionBankDetailSerializer(QuestionBankSerializer):
    """Detailed serializer with questions list"""
    questions = serializers.SerializerMethodField()
    
    class Meta:
        model = QuestionBank
        fields = [
            'id', 'name', 'description', 'subject', 'subject_id',
            'status', 'questions_count',
            'total_questions_count', 'approved_questions_count', 
            'pending_questions_count', 'rejected_questions_count',
            'difficulty_distribution', 'created_at', 'updated_at',
            'questions'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_questions(self, obj):
        """Get all questions in this bank (faqat tasdiqlangan)"""
        bank_questions = BankQuestion.objects.filter(
            bank=obj,
            question__status='APPROVED'
        ).select_related('question', 'question__topic', 'question__section', 'question__subject', 'question__difficulty_level')
        return BankQuestionSerializer(bank_questions, many=True).data


class OrderPointDistributionSerializer(serializers.ModelSerializer):
    topic = TopicSerializer(read_only=True)
    topic_id = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(),
        source='topic',
        write_only=True
    )
    section = SectionSerializer(read_only=True)
    section_id = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(),
        source='section',
        write_only=True
    )
    
    class Meta:
        model = OrderPointDistribution
        fields = [
            'id', 'topic', 'topic_id', 'section', 'section_id',
            'questions_count', 'difficulty_level'
        ]


class BankOrderSerializer(serializers.ModelSerializer):
    bank = QuestionBankSerializer(read_only=True)
    bank_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionBank.objects.all(),
        source='bank',
        write_only=True
    )
    admin = UserSerializer(read_only=True)
    point_distributions = OrderPointDistributionSerializer(many=True, required=False)
    
    class Meta:
        model = BankOrder
        fields = [
            'id', 'bank', 'bank_id', 'admin', 'total_questions',
            'easy_count', 'medium_count', 'hard_count', 'deadline',
            'notes', 'status', 'created_at', 'completed_at',
            'point_distributions'
        ]
        read_only_fields = ['admin', 'created_at', 'completed_at']
    
    def create(self, validated_data):
        point_distributions_data = validated_data.pop('point_distributions', [])
        order = BankOrder.objects.create(**validated_data)
        
        for pd_data in point_distributions_data:
            OrderPointDistribution.objects.create(order=order, **pd_data)
        
        return order
    
    def validate(self, data):
        """Validate question counts"""
        total = data.get('total_questions', 0)
        easy = data.get('easy_count', 0)
        medium = data.get('medium_count', 0)
        hard = data.get('hard_count', 0)
        
        if easy + medium + hard != total:
            raise serializers.ValidationError(
                "Qiyinlik bo'yicha savollar yig'indisi umumiy savollar soniga teng bo'lishi kerak"
            )
        
        # Validate point distributions if provided
        point_distributions = data.get('point_distributions', [])
        if point_distributions:
            total_from_points = sum(pd.get('questions_count', 0) for pd in point_distributions)
            if total_from_points != total:
                raise serializers.ValidationError(
                    f"Punktlar bo'yicha savollar yig'indisi ({total_from_points}) umumiy savollar soniga ({total}) teng bo'lishi kerak"
                )
        
        return data


class VariantQuestionSerializer(serializers.ModelSerializer):
    question = QuestionDetailSerializer(read_only=True)
    
    class Meta:
        model = VariantQuestion
        fields = ['id', 'question', 'order']


class TestVariantSerializer(serializers.ModelSerializer):
    questions = VariantQuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestVariant
        fields = ['id', 'variant_number', 'questions', 'created_at']


class TestBookSerializer(serializers.ModelSerializer):
    bank = QuestionBankSerializer(read_only=True)
    bank_id = serializers.PrimaryKeyRelatedField(
        queryset=QuestionBank.objects.filter(status='active'),
        source='bank',
        write_only=True
    )
    created_by = UserSerializer(read_only=True)
    variants = TestVariantSerializer(many=True, read_only=True)
    average_score = serializers.FloatField(read_only=True)
    pass_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = TestBook
        fields = [
            'id', 'title', 'description', 'bank', 'bank_id',
            'variants_count', 'questions_per_variant', 'time_limit',
            'passing_score', 'easy_percentage', 'medium_percentage',
            'hard_percentage', 'shuffle_questions', 'shuffle_options',
            'show_results', 'allow_review', 'require_auth', 'status',
            'created_by', 'created_at', 'published_at', 'total_attempts',
            'average_score', 'pass_rate', 'share_link', 'qr_code', 'variants'
        ]
        read_only_fields = [
            'created_by', 'created_at', 'published_at', 'total_attempts',
            'share_link', 'qr_code'
        ]
    
    def validate(self, data):
        """Validate percentages"""
        easy = data.get('easy_percentage', 0)
        medium = data.get('medium_percentage', 0)
        hard = data.get('hard_percentage', 0)
        
        if easy + medium + hard != 100:
            raise serializers.ValidationError(
                "Qiyinlik foizlari yig'indisi 100% bo'lishi kerak"
            )
        
        return data


class TestAttemptSerializer(serializers.ModelSerializer):
    book = TestBookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=TestBook.objects.filter(status='published'),
        source='book',
        write_only=True
    )
    variant = TestVariantSerializer(read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=TestVariant.objects.all(),
        source='variant',
        write_only=True
    )
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TestAttempt
        fields = [
            'id', 'book', 'book_id', 'variant', 'variant_id',
            'user', 'score', 'correct_answers', 'wrong_answers',
            'started_at', 'completed_at', 'time_spent'
        ]
        read_only_fields = [
            'user', 'score', 'started_at', 'completed_at'
        ]


