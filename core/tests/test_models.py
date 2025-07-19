from django.test import TestCase
from django.utils import timezone
from core.models import User, Teacher, Student, Exam, Question, StudentExam, StudentAnswer
import datetime
from django.db import IntegrityError
from django.contrib.auth import get_user_model


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(username='teacher1', password='pass1234', role='teacher')
        self.assertEqual(user.username, 'teacher1')
        self.assertEqual(user.role, 'teacher')
        self.assertTrue(user.check_password('pass1234'))

class TeacherModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teachertest', password='pass1234', role='teacher')

    def test_create_teacher(self):
        teacher = Teacher.objects.create(
            user=self.user,
            employee_id='EMP001',
            phone_number='1234567890',
            subject_specialization='Math',
            date_of_joining=timezone.now().date(),
            status=0
        )
        self.assertEqual(teacher.employee_id, 'EMP001')
        self.assertEqual(str(teacher), f"{self.user.get_full_name()} - {teacher.employee_id}")

class StudentModelTest(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(username='teachertest2', password='pass1234', role='teacher')
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP002',
            phone_number='9876543210',
            subject_specialization='Science',
            date_of_joining=timezone.now().date()
        )

        self.student_user = User.objects.create_user(username='studenttest', password='pass1234', role='student')

    def test_create_student(self):
        student = Student.objects.create(
            user=self.student_user,
            roll_number='ROLL001',
            phone_number='1122334455',
            grade='10',
            date_of_birth='2008-05-10',
            admission_date='2023-06-01',
            assigned_teacher=self.teacher
        )
        self.assertEqual(student.roll_number, 'ROLL001')
        self.assertEqual(student.assigned_teacher, self.teacher)
        self.assertEqual(str(student), f"{self.student_user.get_full_name()} - {student.roll_number}")
User = get_user_model()

class ExamModelsTestCase(TestCase):
    def setUp(self):
       
        self.teacher_user = User.objects.create_user(username='teacher1', password='pass1234', role='teacher')
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            phone_number='1234567890',
            subject_specialization='Math',
            date_of_joining=timezone.now().date(),
            status=0
        )

        
        self.student_user = User.objects.create_user(username='student1', password='pass1234', role='student')
        self.student = Student.objects.create(
            user=self.student_user,
            roll_number='ROLL001',
            phone_number='1122334455',
            grade='10',
            date_of_birth='2008-05-10',
            admission_date='2023-06-01',
            assigned_teacher=self.teacher,
            status=0
        )

     
        self.admin_user = User.objects.create_user(username='admin1', password='admin123', role='admin')

       
        self.exam = Exam.objects.create(
            title="Midterm Math",
            subject="Mathematics",
            teacher=self.teacher,
            created_by=self.admin_user
        )

       
        self.question1 = Question.objects.create(
            exam=self.exam,
            question_text="2 + 2 = ?",
            option1="3",
            option2="4",
            option3="5",
            option4="6",
            correct_option="2"
        )

        self.question2 = Question.objects.create(
            exam=self.exam,
            question_text="5 * 2 = ?",
            option1="10",
            option2="20",
            option3="15",
            option4="5",
            correct_option="1"
        )

        
        self.student_exam = StudentExam.objects.create(
            student=self.student,
            exam=self.exam,
            marks=10
        )

      
        self.answer1 = StudentAnswer.objects.create(
            student_exam=self.student_exam,
            question=self.question1,
            answer="2",
            is_correct=False
        )

        self.answer2 = StudentAnswer.objects.create(
            student_exam=self.student_exam,
            question=self.question2,
            answer="1",
            is_correct=True
        )

    def test_exam_creation(self):
        self.assertEqual(self.exam.title, "Midterm Math")
        self.assertEqual(str(self.exam), "Midterm Math")

    def test_question_creation(self):
        self.assertEqual(self.question1.correct_option, "2")
        self.assertEqual(str(self.question1), "2 + 2 = ?")

    def test_student_exam_creation(self):
        self.assertEqual(self.student_exam.exam, self.exam)
        self.assertEqual(self.student_exam.student, self.student)
        self.assertEqual(str(self.student_exam), f"{self.student.user.username} - {self.exam.title}")

    def test_student_answer_creation(self):
        self.assertEqual(self.answer1.question, self.question1)
        self.assertFalse(self.answer1.is_correct)
        self.assertEqual(str(self.answer1), f"{self.student_exam} - Q{self.question1.id} Answer")

    def test_exam_questions_relation(self):
        self.assertEqual(self.exam.questions.count(), 2)

    def test_student_exam_answer_relation(self):
        self.assertEqual(self.student_exam.answers.count(), 2)

    def test_unique_student_exam_constraint(self):
        with self.assertRaises(IntegrityError):
            StudentExam.objects.create(student=self.student, exam=self.exam)