from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return self.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100,default='Unknown')
    last_name = models.CharField(max_length=100,default='Unknown')
    employee_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    subject_specialization = models.CharField(max_length=100)
    date_of_joining = models.DateField()
    status = models.IntegerField(default=0)  

    def delete(self, *args, **kwargs):
        user = self.user  # store user before deletion
        super().delete(*args, **kwargs)
        user.delete()     # now safely delete user

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100,default='Unknown')
    last_name = models.CharField(max_length=100,default='Unknown')
    class_name = models.CharField(max_length=50,default='1')
    roll_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    grade = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    admission_date = models.DateField()
    status = models.IntegerField(default=0)  
    assigned_teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)

    def delete(self, *args, **kwargs):
        user = self.user  
        super().delete(*args, **kwargs)
        user.delete()     

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.roll_number}"


class Exam(models.Model):
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=100)
    target_class = models.CharField(max_length=10,default='1')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    exam = models.ForeignKey(Exam, related_name='questions', on_delete=models.CASCADE)
    question_text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    CORRECT_OPTION_CHOICES = [
        ("1", "Option 1"),
        ("2", "Option 2"),
        ("3", "Option 3"),
        ("4", "Option 4"),
    ]

    correct_option = models.CharField(
        max_length=1,
        choices=CORRECT_OPTION_CHOICES,
        help_text="Enter the correct option number (1-4)"
    )

    def __str__(self):
        return self.question_text



class StudentExam(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    marks = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'exam')

    def __str__(self):
        return f"{self.student.user.username} - {self.exam.title}"

class StudentAnswer(models.Model):
    student_exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student_exam} - Q{self.question.id} Answer"