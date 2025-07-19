from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import User, Teacher, Student
from datetime import date

class ViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        
        self.admin_user = User.objects.create_user(
            username='admin', password='adminpass', role='admin', email='admin@example.com')
        self.client.force_authenticate(user=self.admin_user)

        
        self.teacher_user = User.objects.create_user(
            username='teacher1', password='teachpass', role='teacher', email='teach@example.com')
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id="EMP001",
            phone_number="1234567890",
            subject_specialization="Math",
            date_of_joining=date.today(),
            status=0
        )

        self.student_user = User.objects.create_user(
            username='student1', password='studpass', role='student', email='stud@example.com')
        self.student = Student.objects.create(
            user=self.student_user,
            roll_number="R001",
            phone_number="9999999999",
            grade="10",
            date_of_birth=date(2010, 1, 1),
            admission_date=date.today(),
            assigned_teacher=self.teacher,
            status=0
        )

    def test_admin_can_list_teachers(self):
        response = self.client.get(reverse('teacher-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_admin_can_list_students(self):
        response = self.client.get(reverse('student-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_teacher_can_list_own_students(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(reverse('teacher-students-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        students = response.data["results"]  # Handle paginated data
        self.assertEqual(len(students), 1)
        self.assertEqual(students[0]["user"]["username"], "student1")


    def test_teacher_cannot_access_other_students(self):
        other_teacher_user = User.objects.create_user(
            username='teacher2', password='teachpass2', role='teacher')
        other_teacher = Teacher.objects.create(
            user=other_teacher_user,
            employee_id="EMP002",
            phone_number="2222222222",
            subject_specialization="Science",
            date_of_joining=date.today(),
            status=0
        )
        self.client.force_authenticate(user=other_teacher_user)
        url = reverse('teacher-students-detail', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_teacher_can_update_own_student_except_assigned_teacher(self):
        self.client.force_authenticate(user=self.teacher_user)
        url = reverse('teacher-students-detail', kwargs={'pk': self.student.id})
        data = {
            "grade": "11",
            "assigned_teacher": self.teacher.id  # Should be ignored with warning
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["grade"], "11")
        self.assertIn("warning", response.data)
        self.assertEqual(
            response.data["warning"],
            "Assigned teacher can only be changed by admin."
        )

    def test_export_students_csv(self):
        url = reverse('export_students_csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('student1', response.content.decode())

    def test_export_teachers_csv(self):
        url = reverse('export_teachers_csv')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('teacher1', response.content.decode())


    def test_unauthenticated_user_cannot_list_teachers(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('teacher-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_retrieve_student(self):
        url = reverse('student-detail', kwargs={'pk': self.student.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'student1')

    def test_teacher_cannot_list_all_teachers(self):
        self.client.force_authenticate(user=self.teacher_user)
        response = self.client.get(reverse('teacher-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_student_cannot_list_teachers(self):
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(reverse('teacher-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

