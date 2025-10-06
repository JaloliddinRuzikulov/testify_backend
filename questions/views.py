from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
import os
import uuid
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
from users.permissions import IsAdmin, IsExpert, IsCreator, IsAdminOrExpert, CanEditQuestion


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
    filterset_fields = ['subject', 'topic', 'section', 'difficulty', 'status', 'created_by', 'question_type', 'parent_question']
    search_fields = ['text', 'reading_text', 'subject__name', 'topic__name', 'section__name']
    ordering_fields = ['created_at', 'updated_at', 'reviewed_at', 'difficulty', 'question_order']
    
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
            return [IsAuthenticated(), CanEditQuestion()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Question.objects.all()

        # By default, exclude child questions (they'll be included in parent's serializer)
        # Unless specifically filtering for parent_question
        if 'parent_question' not in self.request.query_params:
            queryset = queryset.filter(parent_question__isnull=True)

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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsExpert])
    def for_review(self, request):
        """Get questions that need review (excluding user's own)"""
        user = request.user

        # Build query for questions that need review
        query = Q(status='SUBMITTED')

        # Exclude user's own questions - IMPORTANT!
        query &= ~Q(created_by=user)

        # Q_EXPERT can only see questions from their assigned subject
        if user.is_q_expert and user.expert_subject:
            query &= Q(subject=user.expert_subject)

        questions = Question.objects.filter(query).select_related(
            'subject', 'topic', 'section', 'created_by'
        ).prefetch_related('options')

        # Paginate if needed
        page = self.paginate_queryset(questions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsExpert])
    def pending_count(self, request):
        """Get count of pending questions for review"""
        user = request.user

        # Build query for questions that need review
        query = Q(status='SUBMITTED')

        # Exclude user's own questions
        query &= ~Q(created_by=user)

        # Q_EXPERT can only see questions from their assigned subject
        if user.is_q_expert and user.expert_subject:
            query &= Q(subject=user.expert_subject)

        count = Question.objects.filter(query).count()

        return Response({
            'pending_count': count,
            'user_role': user.role,
            'subject_filter': user.expert_subject.name if user.expert_subject else None
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsExpert])
    def review(self, request, pk=None):
        """Action for experts to review a question"""
        question = self.get_object()
        user = request.user

        # Users cannot review their own questions
        if question.created_by == user:
            return Response(
                {"detail": "Siz o'zingiz yaratgan savollarni tasdiqlay olmaysiz."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Q_EXPERT can only review questions from their assigned subject
        if user.is_q_expert and user.expert_subject:
            if question.subject != user.expert_subject:
                return Response(
                    {"detail": "Siz faqat o'z faningiz bo'yicha savollarni tekshira olasiz."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(question, data=request.data)

        if serializer.is_valid():
            # Add reviewer info
            serializer.save(reviewed_by=user, reviewed_at=timezone.now())
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionImageUploadView(APIView):
    """View for handling question image uploads"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, format=None):
        """Handle image upload for questions"""
        file_obj = request.FILES.get('image')
        
        if not file_obj:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
        file_extension = os.path.splitext(file_obj.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return Response(
                {'error': f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File size too large. Maximum size is 5MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Ensure media directory exists
        media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        questions_dir = os.path.join(media_root, 'questions')
        os.makedirs(questions_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(questions_dir, unique_filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        # Generate full URL path
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        # Build full URL including host
        host = request.get_host()  # Gets localhost:8001 or actual domain
        protocol = 'https' if request.is_secure() else 'http'
        image_url = f"{protocol}://{host}{media_url}questions/{unique_filename}"
        
        # Generate LaTeX reference
        latex_reference = f"\\includegraphics[width=0.8\\textwidth]{{{image_url}}}"
        
        return Response({
            'id': str(uuid.uuid4()),
            'path': image_url,
            'latex_reference': latex_reference,
            'filename': unique_filename,
            'size': file_obj.size,
            'type': file_obj.content_type
        }, status=status.HTTP_201_CREATED)