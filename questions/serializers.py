from rest_framework import serializers
from django.utils import timezone
from .models import Subject, Topic, Section, Question, QuestionOption, Difficulty


class DifficultySerializer(serializers.ModelSerializer):
    """Serializer for Difficulty model"""
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Difficulty
        fields = ['id', 'name', 'code', 'level', 'description', 'is_active', 
                  'questions_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_questions_count(self, obj):
        return obj.questions.filter(status='APPROVED').count()


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description']


class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model"""
    subject_name = serializers.ReadOnlyField(source='subject.name')
    
    class Meta:
        model = Topic
        fields = ['id', 'subject', 'subject_name', 'number', 'name', 'description']


class SectionSerializer(serializers.ModelSerializer):
    """Serializer for Section model"""
    topic_name = serializers.ReadOnlyField(source='topic.name')
    topic_number = serializers.ReadOnlyField(source='topic.number')
    subject_name = serializers.ReadOnlyField(source='topic.subject.name')
    
    class Meta:
        model = Section
        fields = ['id', 'topic', 'topic_name', 'topic_number', 
                  'subject_name', 'number', 'name', 'description']
        

class QuestionOptionSerializer(serializers.ModelSerializer):
    """Serializer for QuestionOption model"""
    
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for listing questions"""

    subject_name = serializers.ReadOnlyField(source='subject.name')
    topic_name = serializers.ReadOnlyField(source='topic.name')
    topic_number = serializers.ReadOnlyField(source='topic.number')
    section_name = serializers.ReadOnlyField(source='section.name')
    section_number = serializers.ReadOnlyField(source='section.number')
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')
    child_questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_name', 'topic_number',
            'section', 'section_name', 'section_number', 'question_type',
            'difficulty', 'text', 'status', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'reviewed_by',
            'reviewed_by_username', 'reviewed_at', 'child_questions_count'
        ]

    def get_child_questions_count(self, obj):
        if obj.question_type == 'READING':
            return obj.child_questions.count()
        return 0


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Serializer for question details"""

    options = QuestionOptionSerializer(many=True, read_only=True)
    subject = SubjectSerializer(read_only=True)
    topic = TopicSerializer(read_only=True)
    section = SectionSerializer(read_only=True)
    difficulty_level = DifficultySerializer(read_only=True)
    subject_name = serializers.ReadOnlyField(source='subject.name')
    topic_name = serializers.ReadOnlyField(source='topic.name')
    topic_number = serializers.ReadOnlyField(source='topic.number')
    section_name = serializers.ReadOnlyField(source='section.name')
    section_number = serializers.ReadOnlyField(source='section.number')
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')
    child_questions = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_name', 'topic_number',
            'section', 'section_name', 'section_number', 'question_type',
            'reading_text', 'parent_question', 'question_order',
            'difficulty', 'difficulty_level', 'text', 'additional_text', 'image',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
            'status', 'reviewed_by', 'reviewed_by_username', 'reviewed_at',
            'review_comment', 'options', 'child_questions'
        ]

    def get_child_questions(self, obj):
        if obj.question_type == 'READING':
            # Return child questions with their options
            child_serializer = QuestionDetailSerializer(
                obj.child_questions.order_by('question_order'),
                many=True,
                context=self.context
            )
            return child_serializer.data
        return []


class QuestionOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating question options"""
    
    class Meta:
        model = QuestionOption
        fields = ['text', 'is_correct', 'order']


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions with options"""

    options = QuestionOptionCreateSerializer(many=True, required=False)
    child_questions = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Question
        fields = [
            'subject', 'topic', 'section', 'difficulty', 'question_type',
            'reading_text', 'parent_question', 'question_order',
            'text', 'additional_text', 'image', 'options', 'child_questions'
        ]

    def validate(self, attrs):
        # Validate that subject, topic, and section are provided
        if not attrs.get('subject'):
            raise serializers.ValidationError({
                'subject': 'Fan tanlanishi kerak'
            })

        if not attrs.get('topic'):
            raise serializers.ValidationError({
                'topic': 'Mavzu tanlanishi kerak'
            })

        if not attrs.get('section'):
            raise serializers.ValidationError({
                'section': "Bo'lim tanlanishi kerak"
            })

        question_type = attrs.get('question_type', 'SINGLE')

        if question_type == 'READING':
            # For reading questions, we need reading_text and child_questions
            if not attrs.get('reading_text'):
                raise serializers.ValidationError({
                    'reading_text': 'Reading text is required for READING type questions'
                })
            if not attrs.get('child_questions'):
                raise serializers.ValidationError({
                    'child_questions': 'At least one child question is required for READING type'
                })
        else:
            # For non-reading questions, validate options
            options = attrs.get('options', [])
            if not options:
                raise serializers.ValidationError({
                    'options': 'Options are required for non-READING questions'
                })
            if not any(option.get('is_correct', False) for option in options):
                raise serializers.ValidationError({
                    'options': 'At least one option must be marked as correct'
                })

        return attrs

    def create(self, validated_data):
        # Extract options and child questions data
        options_data = validated_data.pop('options', [])
        child_questions_data = validated_data.pop('child_questions', [])

        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user

        # Create main question
        question = Question.objects.create(**validated_data)

        if question.question_type == 'READING':
            # Create child questions for reading comprehension
            for idx, child_data in enumerate(child_questions_data, 1):
                child_options = child_data.pop('options', [])
                child_question = Question.objects.create(
                    parent_question=question,
                    subject=question.subject,
                    topic=question.topic,
                    section=question.section,
                    difficulty=question.difficulty,
                    question_type='SINGLE',  # Child questions are single choice
                    question_order=idx,
                    text=child_data.get('text', ''),
                    created_by=self.context['request'].user
                )

                # Create options for child question
                for option_data in child_options:
                    QuestionOption.objects.create(
                        question=child_question,
                        **option_data
                    )
        else:
            # Create options for regular question
            for option_data in options_data:
                QuestionOption.objects.create(question=question, **option_data)

        return question


class QuestionReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviewing questions"""
    
    class Meta:
        model = Question
        fields = ['status', 'review_comment']
    
    def update(self, instance, validated_data):
        validated_data['reviewed_by'] = self.context['request'].user
        validated_data['reviewed_at'] = timezone.now()
        return super().update(instance, validated_data)