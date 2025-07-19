from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser  
from rest_framework import status, viewsets, permissions, generics
from .serializers import (
    TeacherSerializer, StudentSerializer, ExamSerializer, 
    ExamSubmissionSerializer, StudentExamSerializer, QuestionSerializer,
    TeacherSelfUpdateSerializer
)
from .models import Teacher, Student, Exam, Question, StudentExam, StudentAnswer, User
from django.db import models
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.contrib.auth import authenticate
from .permissions import IsAdmin, IsTeacher, IsAdminOrSelf
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import RetrieveUpdateAPIView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
import csv
import io
from django.http import HttpResponse
import logging


logger = logging.getLogger(__name__)


class CustomLoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        logger.info(f"Login attempt for username: {username}")
        
        if not username or not password:
            return Response(
                {"error": "Please provide both username and password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            logger.error(f"Invalid login for username: {username}")
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        logger.info(f"Login successful for user: {user.username}")
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "full_name": user.get_full_name()
        }, status=status.HTTP_200_OK)


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        elif self.action in ['retrieve', 'list']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Teacher.objects.all()
        elif user.role == 'teacher':
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()

    def create(self, request, *args, **kwargs):
        logger.info(f"[ADMIN:{request.user.username}] Creating a new teacher")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()
        
        return Response({
            "message": "Teacher created successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

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
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]  
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrSelf()]
        elif self.action in ['retrieve', 'list']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

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
       
        if request.user.role not in ['admin', 'teacher']:
            raise PermissionDenied("Only admin and teachers can create students.")
            
        logger.info(f"[{request.user.role.upper()}:{request.user.username}] Creating a new student")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        
        return Response({
            "message": "Student created successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        student = self.get_object()
        logger.info(f"[{request.user.role.upper()}:{request.user.username}] Updating student ID {student.id}")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        student = self.get_object()
        logger.warning(f"[{request.user.role.upper()}:{request.user.username}] Deleting student ID {student.id}")
        return super().destroy(request, *args, **kwargs)


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

    def create(self, request, *args, **kwargs):
       
        logger.info(f"[TEACHER:{request.user.username}] Creating student")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        response_data = serializer.data
        
      
        if 'assigned_teacher' in request.data and request.user.role != 'admin':
            response_data['warning'] = "Assigned teacher can only be changed by admin."

        return Response(response_data)


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


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['attend']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.role == 'student':
            try:
                student = Student.objects.get(user=user)
                return Exam.objects.filter(target_class=student.class_name)
            except Student.DoesNotExist:
                return Exam.objects.none()
           
            student_class = student.class_name
            
            
            student_numeric_class = ''.join(filter(str.isdigit, student_class))
            
          
            return Exam.objects.filter(
                models.Q(target_class=student_class) |  
                models.Q(target_class=student_numeric_class)    
            )
        elif user.role == 'admin':
            return Exam.objects.all()

        return Exam.objects.none()

    def create(self, request, *args, **kwargs):
       
        if request.user.role not in ['admin', 'teacher']:
            raise PermissionDenied("Only admin and teachers can create exams.")
            
        logger.info(f"[{request.user.role.upper()}:{request.user.username}] Creating exam")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = serializer.save()
        
        return Response({
            "message": "Exam created successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def questions(self, request, pk=None):
        exam = self.get_object()
        questions = exam.questions.all()
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
   
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def attend(self, request, pk=None):
        if request.user.role != 'student':
            raise PermissionDenied("Only students can attend exams.")
            
        exam = self.get_object()
        serializer = ExamSubmissionSerializer(
            data=request.data, 
            context={'request': request, 'exam': exam}
        )
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        return Response({
            "message": f"Exam submitted successfully. You scored {submission.marks}/5.",
            "marks": submission.marks,
            "total": 5
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_marks(self, request):
        if request.user.role != 'student':
            raise PermissionDenied("Only students can view their marks.")
            
        try:
            student = Student.objects.get(user=request.user)
            exams = StudentExam.objects.filter(student=student)
            serializer = StudentExamSerializer(exams, many=True)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)


class StudentExamListView(generics.ListAPIView):
    serializer_class = StudentExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StudentExam.objects.all()

        if user.role == 'admin':
            pass 
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

        return queryset.select_related('exam', 'student__user')



@api_view(['GET'])
@permission_classes([IsAdmin]) 
def export_students_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'First Name', 'Last Name', 'Email', 
        'Roll Number', 'Class', 'Grade', 'Phone', 'Assigned Teacher'
    ])

    students = Student.objects.select_related('user', 'assigned_teacher__user')

    for student in students:
        user = student.user
        teacher_name = student.assigned_teacher.user.get_full_name() if student.assigned_teacher else 'None'
        writer.writerow([
            student.id,
            user.username,
            user.first_name,       
            user.last_name,
            user.email,
            student.roll_number,
            student.class_name,
            student.grade,
            student.phone_number,
            teacher_name
        ])

    return response


@api_view(['GET'])
@permission_classes([IsAdmin])  
def export_teachers_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teachers.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'First Name', 'Last Name', 'Email', 
        'Employee ID', 'Specialization', 'Phone', 'Date of Joining'
    ])

    for teacher in Teacher.objects.select_related('user'):
        user = teacher.user
        writer.writerow([
            teacher.id,
            user.username,
            user.first_name,
            user.last_name,
            user.email,
            teacher.employee_id,
            teacher.subject_specialization,
            teacher.phone_number,
            teacher.date_of_joining
        ])

    return response


@api_view(['POST'])
@permission_classes([IsAdmin])
@parser_classes([MultiPartParser])
def import_students_csv(request):
    csv_file = request.FILES.get('file')
    if not csv_file:
        return Response({"error": "CSV file is missing."}, status=status.HTTP_400_BAD_REQUEST)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "Only CSV files are accepted."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2): 
            try:
               
                user = User.objects.create_user(
                    username=row['username'],
                    email=row['email'],
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    password="default123",
                    role='student'
                )

               
                student = Student.objects.create(
                    user=user,
                    roll_number=row['roll_number'],  
                    phone_number=row['phone_number'],
                    grade=row['grade'],
                    class_name=row.get('class_name', '1'),
                    date_of_birth=datetime.strptime(row['date_of_birth'], '%Y-%m-%d').date(),
                    admission_date=datetime.strptime(row['admission_date'], '%Y-%m-%d').date(),
                    assigned_teacher_id=row.get('assigned_teacher_id') if row.get('assigned_teacher_id') else None,
                    status=0
                )

                created_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        if errors:
            return Response({
                "message": f"Imported {created_count} students with {len(errors)} errors.",
                "errors": errors[:10]  
            }, status=status.HTTP_206_PARTIAL_CONTENT)

        return Response({
            "message": f"Successfully imported {created_count} students."
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "error": f"Error processing CSV file: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)



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