from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from .views import (
    # RegisterTeacherView,
    # RegisterStudentView,
    TeacherViewSet,
    StudentViewSet,
    StudentByTeacherViewSet,
    CustomLoginView,
    AdminTeacherViewSet,
    TeacherSelfUpdateView,
    export_students_csv,
    export_teachers_csv,
    import_students_csv,
    ExamViewSet,
    StudentExamListView,
    CustomPasswordResetView,
    CustomPasswordResetConfirmView
)

router = DefaultRouter()
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'mystudents', StudentByTeacherViewSet, basename='teacher-students')
router.register(r'teacher-admin', AdminTeacherViewSet, basename='admin-teacher')
router.register(r'exams', ExamViewSet, basename='exam')
urlpatterns = [
    path('login', CustomLoginView.as_view(), name='custom_login'),
    path('teacher/me', TeacherSelfUpdateView.as_view(), name='teacher_self_update'),
    path('export/students', export_students_csv, name='export_students_csv'),
    path('export/teachers', export_teachers_csv, name='export_teachers_csv'),
    path('student-exams/', StudentExamListView.as_view(), name='student-exam-list'),
    path('import/students', import_students_csv, name='import_students_csv'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('api/student-marks/', StudentExamListView.as_view(), name='student-exam-marks'),
    path('api/password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('api/password-reset-confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('', include(router.urls)),
]
