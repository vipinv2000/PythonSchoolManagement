from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Teacher, Student,User, Exam, Question, StudentExam, StudentAnswer
from core.serializers import (StudentSerializer, ExamSerializer,
    ExamSubmissionSerializer,
    StudentExamSerializer,
    StudentAnswerSerializer,
)
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError
from datetime import date

User = get_user_model()

class StudentSerializerTest(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            email='teacher1@example.com',
            password='testpass123',
            role='teacher'
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            phone_number='9999999999',
            subject_specialization='CS',
            date_of_joining=date(2022, 10, 10)
        )

        
        self.student_data = {
            'user': {
                'username': 'student1',
                'email': 'student1@example.com',
                'password': 'pass1234',
                'role': 'student'
            },
            'roll_number': 'ROLL001',
            'phone_number': '1111111111',
            'grade': '10',
            'date_of_birth': '2007-01-11',
            'admission_date': '2024-05-03',
            'status': 0,
            'assigned_teacher': self.teacher.id
        }

    def test_valid_student_serializer(self):
        serializer = StudentSerializer(data=self.student_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_student_creation(self):
        serializer = StudentSerializer(data=self.student_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        student = serializer.save()

        self.assertEqual(student.roll_number, 'ROLL001')
        self.assertEqual(student.assigned_teacher, self.teacher)
        self.assertEqual(student.user.username, 'student1')

    def test_missing_required_fields(self):
        invalid_data = self.student_data.copy()
        invalid_data.pop('roll_number')

        serializer = StudentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('roll_number', serializer.errors)



class StudentSerializerTest(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            email='teacher1@example.com',
            password='testpass123',
            role='teacher'
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            phone_number='9999999999',
            subject_specialization='CS',
            date_of_joining=date(2022, 10, 10)
        )

        self.student_data = {
            'user': {
                'username': 'student1',
                'email': 'student1@example.com',
                'password': 'pass1234',
                'role': 'student'
            },
            'roll_number': 'ROLL001',
            'phone_number': '1111111111',
            'grade': '10',
            'date_of_birth': '2007-01-11',
            'admission_date': '2024-05-03',
            'status': 0,
            'assigned_teacher': self.teacher.id
        }

    def test_valid_student_serializer(self):
        serializer = StudentSerializer(data=self.student_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_student_creation(self):
        serializer = StudentSerializer(data=self.student_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        student = serializer.save()

        self.assertEqual(student.roll_number, 'ROLL001')
        self.assertEqual(student.assigned_teacher, self.teacher)
        self.assertEqual(student.user.username, 'student1')

    def test_missing_required_fields(self):
        invalid_data = self.student_data.copy()
        invalid_data.pop('roll_number')

        serializer = StudentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('roll_number', serializer.errors)


class ExamSerializerTest(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            email='teacher1@example.com',
            password='testpass123',
            role='teacher'
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP001',
            phone_number='9999999999',
            subject_specialization='CS',
            date_of_joining=date(2022, 10, 10)
        )

        self.questions_data = [
            {
                'question_text': f'Question {i}',
                'option1': 'A',
                'option2': 'B',
                'option3': 'C',
                'option4': 'D',
                'correct_option': '1'  
            } for i in range(1, 6)
        ]

        self.exam_data = {
            'title': 'Math Exam',
            'subject': 'Math',
            'questions': self.questions_data
        }

    def test_valid_exam_creation_by_teacher(self):
        factory = APIRequestFactory()
        request = factory.post('/exams/', self.exam_data, format='json')
        request.user = self.teacher_user

        serializer = ExamSerializer(data=self.exam_data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        exam = serializer.save()

        self.assertEqual(exam.title, 'Math Exam')
        self.assertEqual(exam.teacher, self.teacher)
        self.assertEqual(exam.questions.count(), 5)  

    def test_exam_with_less_than_5_questions(self):
        data = self.exam_data.copy()
        data['questions'] = data['questions'][:3]

        factory = APIRequestFactory()
        request = factory.post('/exams/', data, format='json')
        request.user = self.teacher_user

        serializer = ExamSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)  
        with self.assertRaises(ValidationError):
            serializer.save()  


class ExamSubmissionSerializerTest(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='pass1234',
            role='student'
        )
        self.teacher_user = User.objects.create_user(
            username='teacher2',
            email='teacher2@example.com',
            password='pass1234',
            role='teacher'
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP002',
            phone_number='8888888888',
            subject_specialization='Math',
            date_of_joining=date(2023, 1, 1)
        )

        self.student = Student.objects.create(
            user=self.student_user,
            roll_number='ROLL002',
            phone_number='1234567890',
            grade='10',
            date_of_birth='2007-05-01',
            admission_date='2022-06-10',
            assigned_teacher=self.teacher
        )

        self.exam = Exam.objects.create(
            title='Science Exam',
            subject='Science',
            teacher=self.teacher,
            created_by=self.teacher_user
        )

        self.questions = []
        for i in range(5):
            question = Question.objects.create(
                exam=self.exam,
                question_text=f'Q{i+1}',
                option1='A',
                option2='B',
                option3='C',
                option4='D',
                correct_option='1' 
            )
            self.questions.append(question)

        self.answers_data = [{'question_id': q.id, 'answer': q.correct_option} for q in self.questions]


    def test_valid_exam_submission(self):
        factory = APIRequestFactory()
        request = factory.post('/submit/', {'answers': self.answers_data}, format='json')
        request.user = self.student_user

        serializer = ExamSubmissionSerializer(
            data={'answers': self.answers_data},
            context={'request': request, 'exam': self.exam}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        student_exam = serializer.save()

        self.assertEqual(student_exam.student, self.student)
        self.assertEqual(student_exam.exam, self.exam)
        self.assertEqual(student_exam.marks, 5) 

    def test_duplicate_exam_submission(self):
        StudentExam.objects.create(student=self.student, exam=self.exam)

        factory = APIRequestFactory()
        request = factory.post('/submit/', {'answers': self.answers_data}, format='json')
        request.user = self.student_user

        serializer = ExamSubmissionSerializer(
            data={'answers': self.answers_data},
            context={'request': request, 'exam': self.exam}
        )
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(ValidationError):
            serializer.save() 
    def test_submission_with_incorrect_question(self):
        self.answers_data[0]['question_id'] = 9999  

        factory = APIRequestFactory()
        request = factory.post('/submit/', {'answers': self.answers_data}, format='json')
        request.user = self.student_user

        serializer = ExamSubmissionSerializer(
            data={'answers': self.answers_data},
            context={'request': request, 'exam': self.exam}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError):
            serializer.save()


class StudentExamSerializerTest(TestCase):
    def test_fields_in_output(self):
        user = User.objects.create_user(username='stu', email='s@example.com', password='123', role='student')
        teacher = Teacher.objects.create(
            user=User.objects.create_user(username='t', email='t@example.com', password='123', role='teacher'),
            employee_id='EMP003', phone_number='0000000000',
            subject_specialization='Eng', date_of_joining=date(2020, 1, 1)
        )
        student = Student.objects.create(
            user=user, roll_number='R003', phone_number='123', grade='10',
            date_of_birth='2006-05-10', admission_date='2022-01-01', assigned_teacher=teacher
        )
        exam = Exam.objects.create(title='Eng Exam', subject='English', teacher=teacher, created_by=teacher.user)
        student_exam = StudentExam.objects.create(student=student, exam=exam, marks=3)

        question = Question.objects.create(
            exam=exam,
            question_text='Sample?',
            option1='A', option2='B', option3='C', option4='D', correct_option='1' 
        )

        StudentAnswer.objects.create(
            student_exam=student_exam,
            question=question,
            answer='A',
            is_correct=True
        )

        serializer = StudentExamSerializer(student_exam)
        data = serializer.data

        self.assertEqual(data['exam_title'], 'Eng Exam')
        self.assertEqual(data['marks'], 3)
        self.assertIn('answers', data)  
        self.assertEqual(len(data['answers']), 1)
        self.assertEqual(data['answers'][0]['question_text'], 'Sample?')


class StudentAnswerSerializerTest(TestCase):
    def test_fields(self):
        teacher_user = User.objects.create_user(username='t', email='t@example.com', password='123', role='teacher')
        teacher = Teacher.objects.create(
            user=teacher_user, employee_id='EMP004', phone_number='0000000000',
            subject_specialization='History', date_of_joining='2022-02-02'
        )

        student_user = User.objects.create_user(username='s', email='s@example.com', password='123', role='student')
        student = Student.objects.create(
            user=student_user, roll_number='R004', phone_number='321', grade='9',
            date_of_birth='2007-02-02', admission_date='2023-01-01', assigned_teacher=teacher
        )

        exam = Exam.objects.create(title='History Quiz', subject='History', teacher=teacher, created_by=teacher_user)
        question = Question.objects.create(
            exam=exam, question_text='Who was Napoleon?', option1='A', option2='B', option3='C', option4='D', correct_option='1'
        )
        student_exam = StudentExam.objects.create(student=student, exam=exam)
        answer = StudentAnswer.objects.create(student_exam=student_exam, question=question, answer='A', is_correct=True)

        serializer = StudentAnswerSerializer(answer)
        self.assertEqual(serializer.data['question_text'], 'Who was Napoleon?')
        self.assertEqual(serializer.data['is_correct'], True)