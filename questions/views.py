from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Subject, Topic, Question, QuestionOption
from .serializers import (
    SubjectSerializer,
    TopicSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateSerializer,
    QuestionReviewSerializer
)
from users.permissions import IsAdmin, IsExpert, IsCreator, IsAdminOrExpert


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
    ordering_fields = ['name', 'subject__name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for Question model"""
    queryset = Question.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'topic', 'difficulty', 'status', 'created_by']
    search_fields = ['text', 'subject__name', 'topic__name']
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
            return [IsAuthenticated(), IsCreator()]
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
            # Creators can only see approved questions and their own
            queryset = queryset.filter(
                created_by=user
            )
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsExpert])
    def review(self, request, pk=None):
        """Action for experts to review a question"""
        question = self.get_object()
        serializer = self.get_serializer(question, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)