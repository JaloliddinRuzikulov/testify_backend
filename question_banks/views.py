from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count, Avg
from .models import (
    QuestionBank, BankQuestion, BankOrder, BankTopicQuota,
    TestBook, TestVariant, VariantQuestion, TestAttempt
)
from .serializers import (
    QuestionBankSerializer, QuestionBankDetailSerializer, 
    BankQuestionSerializer, BankOrderSerializer, BankTopicQuotaSerializer,
    TestBookSerializer, TestVariantSerializer, TestAttemptSerializer
)
from users.permissions import IsAdmin, IsExpert, IsAdminOrExpert


class BankTopicQuotaViewSet(viewsets.ModelViewSet):
    """Topic Quota CRUD operations"""
    queryset = BankTopicQuota.objects.all()
    serializer_class = BankTopicQuotaSerializer
    permission_classes = [IsAdminOrExpert]
    
    def get_queryset(self):
        """Filter quotas by bank if provided"""
        queryset = super().get_queryset()
        bank_id = self.request.query_params.get('bank')
        
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)
        
        return queryset.select_related('bank', 'topic', 'section', 'difficulty')
    
    def perform_create(self, serializer):
        """Update current_count after creating quota"""
        quota = serializer.save()
        self.update_current_count(quota)
    
    def update_current_count(self, quota):
        """Update the current count based on existing questions"""
        from questions.models import Question
        
        # Count approved questions matching this quota
        questions = Question.objects.filter(
            status='APPROVED',
            subject=quota.bank.subject,
            topic=quota.topic
        )
        
        if quota.section:
            questions = questions.filter(section=quota.section)
        
        if quota.difficulty:
            questions = questions.filter(difficulty_level=quota.difficulty)
        
        # Get questions already in the bank
        bank_question_ids = quota.bank.bank_questions.values_list('question_id', flat=True)
        current_count = questions.filter(id__in=bank_question_ids).count()
        
        quota.current_count = current_count
        quota.save(update_fields=['current_count'])


class QuestionBankViewSet(viewsets.ModelViewSet):
    """Question Bank CRUD operations"""
    queryset = QuestionBank.objects.all()
    serializer_class = QuestionBankSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use detail serializer for retrieve action"""
        if self.action == 'retrieve':
            return QuestionBankDetailSerializer
        return QuestionBankSerializer
    
    def get_permissions(self):
        """Different permissions for different actions"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrExpert()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter banks based on user role"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by subject
        subject_filter = self.request.query_params.get('subject')
        if subject_filter:
            queryset = queryset.filter(subject_id=subject_filter)
        
        # All authenticated users can see banks of their subjects
        # Admins can see all banks
        if user.role not in ['ADMIN', 'SUPERADMIN']:
            # QB_EXPERT and Q_EXPERT can work with banks of their subjects
            # TODO: Add user-subject relationship and filter accordingly
            pass
        
        return queryset.select_related('subject')
    
    def perform_create(self, serializer):
        """Create bank"""
        serializer.save()
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminOrExpert])
    def available_questions(self, request, pk=None):
        """Get questions that are not already in any bank"""
        from questions.models import Question
        from questions.serializers import QuestionDetailSerializer
        
        bank = self.get_object()
        
        # Get all question IDs that are already in ANY bank
        used_question_ids = BankQuestion.objects.values_list('question_id', flat=True)
        
        # Filter approved questions that are not in any bank and match the bank's subject
        available_questions = Question.objects.filter(
            status='APPROVED',
            subject=bank.subject
        ).exclude(
            id__in=used_question_ids
        )
        
        # Apply additional filters
        topic_id = request.query_params.get('topic')
        if topic_id:
            available_questions = available_questions.filter(topic_id=topic_id)
        
        difficulty_id = request.query_params.get('difficulty_level')
        if difficulty_id:
            available_questions = available_questions.filter(difficulty_level_id=difficulty_id)
        
        # For backward compatibility, also check old difficulty field
        difficulty_code = request.query_params.get('difficulty')
        if difficulty_code:
            available_questions = available_questions.filter(difficulty=difficulty_code)
        
        serializer = QuestionDetailSerializer(available_questions[:100], many=True)
        
        return Response({
            'count': available_questions.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrExpert])
    def add_questions(self, request, pk=None):
        """Add questions to bank"""
        bank = self.get_object()
        question_ids = request.data.get('question_ids', [])
        
        if not question_ids:
            return Response(
                {'error': 'question_ids majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        added_count = 0
        for question_id in question_ids:
            try:
                bank_question, created = BankQuestion.objects.get_or_create(
                    bank=bank,
                    question_id=question_id,
                    defaults={'added_by': request.user}
                )
                if created:
                    added_count += 1
            except Exception as e:
                continue
        
        return Response({
            'message': f'{added_count} ta savol qo\'shildi',
            'total_questions': bank.questions_count
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrExpert])
    def remove_question(self, request, pk=None):
        """Remove question from bank"""
        bank = self.get_object()
        question_id = request.data.get('question_id')
        
        if not question_id:
            return Response(
                {'error': 'question_id majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            bank_question = BankQuestion.objects.get(
                bank=bank,
                question_id=question_id
            )
            bank_question.delete()
            return Response({
                'message': 'Savol o\'chirildi',
                'total_questions': bank.questions_count
            })
        except BankQuestion.DoesNotExist:
            return Response(
                {'error': 'Savol topilmadi'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAdminOrExpert], url_path='remove-question/(?P<question_id>\\d+)')
    def remove_question_by_id(self, request, pk=None, question_id=None):
        """Remove question from bank by URL parameter"""
        bank = self.get_object()
        
        if not question_id:
            return Response(
                {'error': 'question_id majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            bank_question = BankQuestion.objects.get(
                bank=bank,
                question_id=question_id
            )
            bank_question.delete()
            return Response({
                'message': 'Savol o\'chirildi',
                'total_questions': bank.questions_count
            })
        except BankQuestion.DoesNotExist:
            return Response(
                {'error': 'Savol topilmadi'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAdminOrExpert])
    def limits(self, request, pk=None):
        """Get or set question limits for bank"""
        from .models import BankTopicQuota
        from questions.models import Difficulty
        
        bank = self.get_object()
        
        if request.method == 'GET':
            # Get existing limits from BankTopicQuota
            quotas = BankTopicQuota.objects.filter(bank=bank).select_related(
                'topic', 'section', 'difficulty'
            )
            
            # Group quotas by topic and section
            limits_dict = {}
            
            for quota in quotas:
                if quota.section:
                    # Section-level quota
                    key = f'section_{quota.section.id}'
                    if key not in limits_dict:
                        limits_dict[key] = {
                            'section_id': quota.section.id,
                            'section_name': quota.section.name,
                            'section_number': quota.section.number,
                            'topic_id': quota.topic.id if quota.topic else None,
                            'topic_name': quota.topic.name if quota.topic else None,
                            'topic_number': quota.topic.number if quota.topic else None,
                            'easy_count': 0,
                            'medium_count': 0,
                            'hard_count': 0,
                            'total_count': 0
                        }
                else:
                    # Topic-level quota (no section)
                    key = f'topic_{quota.topic.id}'
                    if key not in limits_dict:
                        limits_dict[key] = {
                            'section_id': None,
                            'section_name': None,
                            'section_number': None,
                            'topic_id': quota.topic.id,
                            'topic_name': quota.topic.name,
                            'topic_number': quota.topic.number,
                            'easy_count': 0,
                            'medium_count': 0,
                            'hard_count': 0,
                            'total_count': 0
                        }
                
                # Add counts based on difficulty code
                if quota.difficulty:
                    if quota.difficulty.code.lower() == 'easy':
                        limits_dict[key]['easy_count'] = quota.target_count
                    elif quota.difficulty.code.lower() == 'medium':
                        limits_dict[key]['medium_count'] = quota.target_count
                    elif quota.difficulty.code.lower() == 'hard':
                        limits_dict[key]['hard_count'] = quota.target_count
                    
                    limits_dict[key]['total_count'] += quota.target_count
            
            return Response({'limits': list(limits_dict.values())})
        
        # POST - Set limits (redirect to set_limits)
        return self.set_limits(request, pk)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrExpert])
    def set_limits(self, request, pk=None):
        """Set question limits for bank"""
        from .models import BankTopicQuota
        from questions.models import Section, Topic, Difficulty
        
        bank = self.get_object()
        limits = request.data.get('limits', [])
        
        if not limits:
            return Response(
                {'error': 'Limitlar majburiy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clear existing quotas for this bank
        BankTopicQuota.objects.filter(bank=bank).delete()
        
        # Create new quotas
        total_questions = 0
        section_count = 0
        topic_count = 0
        
        # Get difficulty objects
        difficulties = {
            'easy': Difficulty.objects.filter(code__iexact='easy').first(),
            'medium': Difficulty.objects.filter(code__iexact='medium').first(),
            'hard': Difficulty.objects.filter(code__iexact='hard').first(),
        }
        
        for limit in limits:
            section_id = limit.get('section_id')
            topic_id = limit.get('topic_id')
            
            if section_id:
                # Section-level quota
                try:
                    section = Section.objects.get(id=section_id)
                    
                    # Create quota for each difficulty level
                    for diff_name in ['easy', 'medium', 'hard']:
                        count = limit.get(f'{diff_name}_count', 0)
                        if count > 0 and difficulties[diff_name]:
                            BankTopicQuota.objects.create(
                                bank=bank,
                                topic=section.topic,
                                section=section,
                                difficulty=difficulties[diff_name],
                                target_count=count
                            )
                            total_questions += count
                    section_count += 1
                except Section.DoesNotExist:
                    continue
                    
            elif topic_id:
                # Topic-level quota (no specific section)
                try:
                    topic = Topic.objects.get(id=topic_id)
                    
                    # Create quota for each difficulty level
                    for diff_name in ['easy', 'medium', 'hard']:
                        count = limit.get(f'{diff_name}_count', 0)
                        if count > 0 and difficulties[diff_name]:
                            BankTopicQuota.objects.create(
                                bank=bank,
                                topic=topic,
                                section=None,  # No specific section
                                difficulty=difficulties[diff_name],
                                target_count=count
                            )
                            total_questions += count
                    topic_count += 1
                except Topic.DoesNotExist:
                    continue
        
        message_parts = []
        if topic_count > 0:
            message_parts.append(f'{topic_count} ta mavzu')
        if section_count > 0:
            message_parts.append(f'{section_count} ta bo\'lim')
        
        message = ' va '.join(message_parts) if message_parts else 'Hech qanday limit'
        
        return Response({
            'message': f'{message} uchun limitlar saqlandi',
            'total_questions': total_questions
        })
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get all questions in bank"""
        bank = self.get_object()
        bank_questions = BankQuestion.objects.filter(
            bank=bank
        ).select_related('question', 'question__topic', 'question__section', 'question__subject', 'question__difficulty_level')
        
        serializer = BankQuestionSerializer(bank_questions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrExpert])
    def activate(self, request, pk=None):
        """Activate bank"""
        bank = self.get_object()
        bank.status = 'active'
        bank.save()
        return Response({'message': 'Bank faollashtirildi'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrExpert])
    def archive(self, request, pk=None):
        """Archive bank"""
        bank = self.get_object()
        bank.status = 'archived'
        bank.save()
        return Response({'message': 'Bank arxivlandi'})


class BankOrderViewSet(viewsets.ModelViewSet):
    """Bank Order management"""
    queryset = BankOrder.objects.all()
    serializer_class = BankOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only admins can create orders"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter orders based on user role"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Experts see orders for their banks
        if user.role == 'EXPERT':
            queryset = queryset.filter(bank__expert=user)
        
        return queryset.select_related('bank', 'admin')
    
    def perform_create(self, serializer):
        """Set admin when creating order"""
        serializer.save(admin=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsExpert])
    def start_processing(self, request, pk=None):
        """Expert starts processing order"""
        order = self.get_object()
        
        if order.status != 'pending':
            return Response(
                {'error': 'Faqat kutilayotgan buyurtmalarni boshlash mumkin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'processing'
        order.save()
        return Response({'message': 'Buyurtma jarayoni boshlandi'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsExpert])
    def complete(self, request, pk=None):
        """Complete order"""
        order = self.get_object()
        
        if order.status != 'processing':
            return Response(
                {'error': 'Faqat jarayondagi buyurtmalarni yakunlash mumkin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if requirements are met
        bank = order.bank
        if bank.questions_count < order.total_questions:
            return Response(
                {'error': f'Bankda yetarli savol yo\'q. Kerak: {order.total_questions}, Mavjud: {bank.questions_count}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.complete()
        return Response({'message': 'Buyurtma yakunlandi'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()
        
        if order.status == 'completed':
            return Response(
                {'error': 'Yakunlangan buyurtmani bekor qilib bo\'lmaydi'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        return Response({'message': 'Buyurtma bekor qilindi'})


class TestBookViewSet(viewsets.ModelViewSet):
    """Test Book management"""
    queryset = TestBook.objects.all()
    serializer_class = TestBookSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only admins can create/edit books"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter books"""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by bank
        bank_filter = self.request.query_params.get('bank')
        if bank_filter:
            queryset = queryset.filter(bank_id=bank_filter)
        
        return queryset.select_related('bank', 'created_by').prefetch_related('variants')
    
    def perform_create(self, serializer):
        """Set creator when creating book"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def publish(self, request, pk=None):
        """Publish book and generate variants"""
        book = self.get_object()
        
        if book.status == 'published':
            return Response(
                {'error': 'Kitob allaqachon nashr etilgan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            book.publish()
            return Response({
                'message': 'Kitob nashr etildi va variantlar yaratildi',
                'share_link': book.share_link,
                'variants_count': book.variants.count()
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def archive(self, request, pk=None):
        """Archive book"""
        book = self.get_object()
        book.status = 'archived'
        book.save()
        return Response({'message': 'Kitob arxivlandi'})
    
    @action(detail=True, methods=['get'])
    def variants(self, request, pk=None):
        """Get all variants of book"""
        book = self.get_object()
        variants = book.variants.prefetch_related('questions__question')
        serializer = TestVariantSerializer(variants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get book statistics"""
        book = self.get_object()
        
        attempts = book.attempts.all()
        
        stats = {
            'total_attempts': book.total_attempts,
            'average_score': book.average_score,
            'pass_rate': book.pass_rate,
            'by_variant': [],
            'recent_attempts': []
        }
        
        # Stats by variant
        for variant in book.variants.all():
            variant_attempts = attempts.filter(variant=variant)
            stats['by_variant'].append({
                'variant_number': variant.variant_number,
                'attempts': variant_attempts.count(),
                'average_score': variant_attempts.aggregate(
                    avg=Avg('score')
                )['avg'] or 0
            })
        
        # Recent attempts
        recent = attempts.order_by('-started_at')[:10]
        stats['recent_attempts'] = TestAttemptSerializer(recent, many=True).data
        
        return Response(stats)


class TestAttemptViewSet(viewsets.ModelViewSet):
    """Test Attempt tracking"""
    queryset = TestAttempt.objects.all()
    serializer_class = TestAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter attempts"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Regular users see only their attempts
        if user.role not in ['ADMIN', 'EXPERT']:
            queryset = queryset.filter(user=user)
        
        # Filter by book
        book_filter = self.request.query_params.get('book')
        if book_filter:
            queryset = queryset.filter(book_id=book_filter)
        
        return queryset.select_related('book', 'variant', 'user')
    
    def perform_create(self, serializer):
        """Set user when creating attempt"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit test answers"""
        attempt = self.get_object()
        
        if attempt.completed_at:
            return Response(
                {'error': 'Test allaqachon yakunlangan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        answers = request.data.get('answers', {})
        correct_count = 0
        wrong_count = 0
        
        # Check answers
        for question in attempt.variant.questions.all():
            user_answer = answers.get(str(question.id))
            if user_answer is not None:
                # Here you would check against correct answer
                # For now, just mock
                import random
                if random.choice([True, False]):
                    correct_count += 1
                else:
                    wrong_count += 1
        
        # Update attempt
        attempt.correct_answers = correct_count
        attempt.wrong_answers = wrong_count
        attempt.completed_at = timezone.now()
        attempt.time_spent = (attempt.completed_at - attempt.started_at).seconds
        attempt.calculate_score()
        
        return Response({
            'score': attempt.score,
            'correct_answers': attempt.correct_answers,
            'wrong_answers': attempt.wrong_answers,
            'passed': attempt.score >= attempt.book.passing_score
        })