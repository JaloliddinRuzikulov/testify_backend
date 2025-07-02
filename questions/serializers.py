from rest_framework import serializers
from django.utils import timezone
from .models import Subject, Topic, Question, QuestionOption


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description']


class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model"""
    
    class Meta:
        model = Topic
        fields = ['id', 'subject', 'name', 'description']
        

class QuestionOptionSerializer(serializers.ModelSerializer):
    """Serializer for QuestionOption model"""
    
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for listing questions"""
    
    subject_name = serializers.ReadOnlyField(source='subject.name')
    topic_name = serializers.ReadOnlyField(source='topic.name')
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')
    
    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_name',
            'difficulty', 'status', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'reviewed_by', 
            'reviewed_by_username', 'reviewed_at'
        ]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Serializer for question details"""
    
    options = QuestionOptionSerializer(many=True, read_only=True)
    subject_name = serializers.ReadOnlyField(source='subject.name')
    topic_name = serializers.ReadOnlyField(source='topic.name')
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')
    
    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_name', 
            'difficulty', 'text', 'additional_text', 'image',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
            'status', 'reviewed_by', 'reviewed_by_username', 'reviewed_at', 
            'review_comment', 'options'
        ]


class QuestionOptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating question options"""
    
    class Meta:
        model = QuestionOption
        fields = ['text', 'is_correct', 'order']


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions with options"""
    
    options = QuestionOptionCreateSerializer(many=True)
    
    class Meta:
        model = Question
        fields = [
            'subject', 'topic', 'difficulty', 'text', 
            'additional_text', 'image', 'options'
        ]
    
    def validate_options(self, options):
        """Validate that at least one option is marked as correct"""
        if not any(option.get('is_correct', False) for option in options):
            raise serializers.ValidationError(
                "At least one option must be marked as correct."
            )
        return options
    
    def create(self, validated_data):
        # Extract options data
        options_data = validated_data.pop('options')
        
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        
        # Create question
        question = Question.objects.create(**validated_data)
        
        # Create options
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