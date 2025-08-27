from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Subject, Topic, Section, Question, QuestionOption, Difficulty
from .serializers import (
    SubjectSerializer,
    TopicSerializer,
    SectionSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateSerializer,
    QuestionReviewSerializer,
    DifficultySerializer
)
from users.permissions import IsAdmin, IsExpert, IsCreator, IsAdminOrExpert


class DifficultyViewSet(viewsets.ModelViewSet):
    """ViewSet for Difficulty model"""
    queryset = Difficulty.objects.filter(is_active=True)
    serializer_class = DifficultySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['level', 'name']
    ordering = ['level']  # Default ordering by level
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Allow admins to see all difficulties including inactive ones
        if self.request.user.role in ['ADMIN', 'SUPERADMIN']:
            queryset = Difficulty.objects.all()
        return queryset


class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Subject model"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]


class TopicViewSet(viewsets.ModelViewSet):
    """ViewSet for Topic model"""
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject']
    search_fields = ['name', 'description', 'subject__name']
    ordering_fields = ['number', 'name', 'subject__name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]


class SectionViewSet(viewsets.ModelViewSet):
    """ViewSet for Section model"""
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['topic', 'topic__subject']
    search_fields = ['name', 'description', 'topic__name', 'topic__subject__name']
    ordering_fields = ['number', 'name', 'topic__number', 'topic__subject__name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for Question model"""
    queryset = Question.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'topic', 'section', 'difficulty', 'status', 'created_by']
    search_fields = ['text', 'subject__name', 'topic__name', 'section__name']
    ordering_fields = ['created_at', 'updated_at', 'reviewed_at', 'difficulty']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QuestionCreateSerializer
        elif self.action == 'review':
            return QuestionReviewSerializer
        elif self.action == 'retrieve':
            return QuestionDetailSerializer
        return QuestionListSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            # Both CREATOR and Q_EXPERT can create questions
            return [IsAuthenticated()]
        elif self.action == 'review':
            return [IsAuthenticated(), IsExpert()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrExpert()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Question.objects.all()
        
        # Filter questions based on user role
        if user.is_creator and not (user.is_admin or user.is_expert):
            # Creators can only see their own questions
            queryset = queryset.filter(
                created_by=user
            )
        elif user.is_q_expert:
            # Q_EXPERT can only see questions from their assigned subject
            if user.expert_subject:
                queryset = queryset.filter(subject=user.expert_subject)
            else:
                # If no subject assigned, return empty queryset
                queryset = queryset.none()
        
        return queryset
    
    def perform_create(self, serializer):
        """Custom create to handle Q_EXPERT subject restriction"""
        user = self.request.user
        
        # If user is Q_EXPERT, ensure they can only create in their assigned subject
        if user.is_q_expert and user.expert_subject:
            # Force the subject to be the expert's assigned subject
            serializer.save(created_by=user, subject=user.expert_subject)
        else:
            serializer.save(created_by=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsExpert])
    def review(self, request, pk=None):
        """Action for experts to review a question"""
        question = self.get_object()
        
        # Q_EXPERT can only review questions from their assigned subject
        user = request.user
        if user.is_q_expert and user.expert_subject:
            if question.subject != user.expert_subject:
                return Response(
                    {"detail": "Siz faqat o'z faningiz bo'yicha savollarni tekshira olasiz."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(question, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)