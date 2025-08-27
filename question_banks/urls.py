from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QuestionBankViewSet, BankOrderViewSet, BankTopicQuotaViewSet,
    TestBookViewSet, TestAttemptViewSet
)

router = DefaultRouter()
router.register('banks', QuestionBankViewSet, basename='questionbank')
router.register('topic-quotas', BankTopicQuotaViewSet, basename='topicquota')
router.register('orders', BankOrderViewSet, basename='bankorder')
router.register('books', TestBookViewSet, basename='testbook')
router.register('attempts', TestAttemptViewSet, basename='testattempt')

urlpatterns = [
    path('', include(router.urls)),
]