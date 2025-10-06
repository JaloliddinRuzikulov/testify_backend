from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, TopicViewSet, SectionViewSet, QuestionViewSet, DifficultyViewSet, QuestionImageUploadView

router = DefaultRouter()
router.register(r'difficulties', DifficultyViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'topics', TopicViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'questions', QuestionViewSet)

urlpatterns = [
    path('upload-image/', QuestionImageUploadView.as_view(), name='question-image-upload'),
    path('', include(router.urls)),
]