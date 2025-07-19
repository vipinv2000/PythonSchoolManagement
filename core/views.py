from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser  
from rest_framework import status,viewsets,permissions,generics
from .serializers import TeacherSerializer, StudentSerializer
from .models import Teacher, Student
from django.db import models
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from .permissions import IsAdmin, IsTeacher,IsAdminOrSelf
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.decorators import parser_classes
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.models import User
from django.core.mail import send_mail
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from .models import Exam, Question, StudentExam, StudentAnswer
from django.utils.http import urlsafe_base64_decode
from .serializers import ExamSerializer,ExamSubmissionSerializer,StudentExamSerializer,QuestionSerializer
from django.contrib.auth import get_user_model
from datetime import datetime
import csv
import io
from django.http import HttpResponse
from .serializers import TeacherSelfUpdateSerializer
import logging




# class RegisterTeacherView(APIView):
#     permission_classes = [IsAdmin]

#     def post(self, request):
#         serializer = TeacherSerializer(data=request.data)
#         if serializer.is_valid():
#             teacher = serializer.save()
#             return Response({
#                 "message": "Teacher registered successfully.",
#                 "teacher_id": teacher.id,
#                 "user_id": teacher.user.id
#             }, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class RegisterStudentView(APIView):
#     permission_classes = [IsAdmin]

#     def post(self, request):
#         serializer = StudentSerializer(data=request.data)
#         if serializer.is_valid():
#             student = serializer.save()
#             return Response({
#                 "message": "Student registered successfully.",
#                 "student_id": student.id,
#                 "user_id": student.user.id
#             }, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


logger = logging.getLogger(__name__)
    
class CustomLoginView(APIView):
    permission_classes = []  

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        logger.info(f"Login attempt for username: {username}")
        if not username or not password:
            return Response({"error": "Please provide both username and password."},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if not user:
            logger.error(f"Invalid login for username: {username}")
            return Response({"error": "Invalid credentials."},
                            status=status.HTTP_401_UNAUTHORIZED)
        logger.info(f"Login successful for user: {user.username}")
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        }, status=status.HTTP_200_OK)




class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]  


    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        elif self.action in ['retrieve']:
            return [IsAuthenticated(), IsAdminOrSelf()]
        return [IsAuthenticated(), IsAdmin()]
    def get_queryset(self):
        user = self.request.user
        print(user.role)
        if user.role == 'admin':
            return Teacher.objects.all()
        elif user.role == 'teacher':
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()

    def create(self, request, *args, **kwargs):
        logger.info(f"[ADMIN:{request.user.username}] Creating a new teacher")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        teacher = self.get_object()
        logger.info(f"[{request.user.role.upper()}:{request.user.username}] Updating teacher ID {teacher.id}")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        teacher = self.get_object()
        logger.warning(f"[{request.user.role.upper()}:{request.user.username}] Deleting teacher ID {teacher.id}")
        return super().destroy(request, *args, **kwargs)


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Student.objects.all()
        elif user.role == 'student':
            return Student.objects.filter(user=user)
        elif user.role == 'teacher':
            return Student.objects.filter(assigned_teacher__user=user)
        return Student.objects.none()

    def create(self, request, *args, **kwargs):
        logger.info(f"[ADMIN:{request.user.username}] Creating a new student")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        student = self.get_object()
        logger.info(f"[ADMIN:{request.user.username}] Updating student ID {student.id}")
        logger.debug(f"Update data: {request.data}")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        student = self.get_object()
        logger.warning(f"[ADMIN:{request.user.username}] Deleting student ID {student.id}")
        return super().destroy(request, *args, **kwargs)
  

# class StudentByTeacherViewSet(viewsets.ReadOnlyModelViewSet):
class StudentByTeacherViewSet(viewsets.ModelViewSet):    
    serializer_class = StudentSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return Student.objects.filter(assigned_teacher__user=self.request.user)
    
    def get_object(self):
        obj = super().get_object()
        if obj.assigned_teacher.user != self.request.user:
            raise PermissionDenied("You do not have permission to access this student.")
        return obj

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = serializer.data
        
        if getattr(serializer, 'warn_assigned_teacher_change', False):
            response_data['warning'] = "Assigned teacher can only be changed by admin."

        return Response(response_data)


    def perform_create(self, serializer):
        serializer.save(assigned_teacher=self.request.user.teacher)

class AdminTeacherViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=['get'], url_path='students')
    def get_students(self, request, pk=None):
        teacher = self.get_object()
        students = Student.objects.filter(assigned_teacher=teacher)
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)
    

class TeacherSelfUpdateView(RetrieveUpdateAPIView):
    serializer_class = TeacherSelfUpdateSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self):
        return self.request.user.teacher
    

@api_view(['GET'])
@permission_classes([IsAdmin]) 
def export_students_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Grade', 'Phone'])

    for student in Student.objects.select_related('user'):
        writer.writerow([student.id, student.user.username, student.grade, student.phone_number])

    return response
@api_view(['GET'])
@permission_classes([IsAdmin])  
def export_teachers_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teachers.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Specialization', 'Phone'])

    for teacher in Teacher.objects.select_related('user'):
        writer.writerow([teacher.id, teacher.user.username, teacher.subject_specialization, teacher.phone_number])

    return response


User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAdmin])
@parser_classes([MultiPartParser])
def import_students_csv(request):
    csv_file = request.FILES.get('file')
    if not csv_file:
        return Response({"error": "CSV file is missing."}, status=status.HTTP_400_BAD_REQUEST)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "Only CSV files are accepted."}, status=status.HTTP_400_BAD_REQUEST)

    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)

    created_count = 0
    for row in reader:
        try:
            user = User.objects.create_user(
                username=row['username'],
                email=row['email'],
                password="default123",
                role='student'
            )

            student = Student.objects.create(
                user=user,
                roll_number=row['roll_number'],  
                phone_number=row['phone_number'],
                grade=row['grade'],
                date_of_birth=datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date(),
                admission_date=datetime.strptime(row['admission_date'], '%Y-%m-%d').date(),
                assigned_teacher=Teacher.objects.get(pk=row['assigned_teacher_id']),
                status=0
            )

            created_count += 1

        except Exception as e:
            return Response({"error": f"Error processing row {row}: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": f"Successfully imported {created_count} students."}, status=status.HTTP_201_CREATED)


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'teacher':
            teacher = Teacher.objects.get(user=user)
            serializer.save(created_by=user, teacher=teacher)
        elif user.role == 'admin':
            serializer.save(created_by=user)
        else:
            raise PermissionError("Only teachers or admins can create exams.")

    def get_queryset(self):
        user = self.request.user

        if user.role == 'student':
            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Exam.objects.none()
            
            return Exam.objects.filter(
                models.Q(target_class=student.class_name) |  # exact match
                models.Q(target_class=student.class_name[:-1])  # same grade, any division (e.g., "10" matches "10A")
            )

        elif user.role in ['admin', 'teacher']:
            return Exam.objects.all()

        return Exam.objects.none()



    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def questions(self, request, pk=None):
        exam = self.get_object()
        questions = exam.questions.all()
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
   
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def attend(self, request, pk=None):
        exam = self.get_object()
        serializer = ExamSubmissionSerializer(data=request.data, context={'request': request, 'exam': exam})
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        return Response({
            "message": f"Submitted successfully. You scored {submission.marks}/5."
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_marks(self, request):
        student = Student.objects.get(user=request.user)
        exams = StudentExam.objects.filter(student=student)
        serializer = StudentExamSerializer(exams, many=True)
        return Response(serializer.data)
    

class StudentExamListView(generics.ListAPIView):
    serializer_class = StudentExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StudentExam.objects.all()

        if user.role == 'admin':
            return queryset

        elif user.role == 'teacher':
            queryset = queryset.filter(student__assigned_teacher__user=user)

        elif user.role == 'student':
            try:
                student = Student.objects.get(user=user)
                queryset = queryset.filter(student=student)
            except Student.DoesNotExist:
                return StudentExam.objects.none()

        exam_id = self.request.query_params.get('exam_id')
        if exam_id:
            queryset = queryset.filter(exam__id=exam_id)

        return queryset


class CustomPasswordResetView(APIView):
    def post(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            send_mail(
                subject="Reset your password",
                message=f"Click the link to reset your password: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({"message": "Reset link sent."}, status=200)
        except User.DoesNotExist:
            return Response({"error": "Email not found."}, status=404)
        
class CustomPasswordResetConfirmView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError):
            return Response({"error": "Invalid UID."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token."}, status=400)

        new_password = request.data.get("password")
        if not new_password:
            return Response({"error": "Password is required."}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password has been reset."})