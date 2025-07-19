from rest_framework import serializers
# from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from core.models import Exam, Question, Teacher
from .models import User, Teacher,Student,StudentExam, StudentAnswer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['user_id'] = user.id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['role'] = self.user.role
        return data



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.get('password')
        if not password:
            raise serializers.ValidationError({'password': 'This field is required.'})
        validated_data['password'] = make_password(password)
        return super().create(validated_data)
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

      
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        return instance

class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'first_name', 'last_name', 'employee_id', 'phone_number', 'subject_specialization', 'date_of_joining', 'status']
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        teacher = Teacher.objects.create(user=user, **validated_data)
        return teacher
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

       
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        return instance
    
class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    assigned_teacher = serializers.PrimaryKeyRelatedField(
    queryset=Teacher.objects.all(),
    required=False  
)

    warn_assigned_teacher_change = False

    class Meta:
        model = Student
        fields = ['id', 'user', 'first_name', 'last_name', 'roll_number', 'phone_number', 'grade', 'class_name', 'date_of_birth', 'admission_date', 'status', 'assigned_teacher']
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        student = Student.objects.create(user=user, **validated_data)
        return student
    


    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        request_user = self.context['request'].user

       
        if getattr(request_user, "role", "") != "admin" and 'assigned_teacher' in validated_data:
            validated_data.pop('assigned_teacher')
            self.warn_assigned_teacher_change = True  

        
        if user_data:
            user_serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

      
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    
class TeacherSelfUpdateSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Teacher
        fields = ['user','phone_number']  

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update phone number
        if 'phone_number' in validated_data:
            instance.phone_number = validated_data['phone_number']
            instance.save()

        return instance

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option'
        ]


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class TeacherMiniSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user']

class ExamSerializer(serializers.ModelSerializer):
    teacher = TeacherMiniSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        required=False
    )
    questions = QuestionSerializer(many=True, write_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'title', 'subject', 'target_class', 'teacher', 'teacher_id', 'questions']


    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        request_user = self.context['request'].user

        if len(questions_data) != 5:
            raise serializers.ValidationError("Each exam must contain exactly 5 questions.")

        if request_user.role == 'teacher':
            teacher = Teacher.objects.get(user=request_user)
            validated_data['teacher'] = teacher

        validated_data['created_by'] = request_user
        exam = Exam.objects.create(**validated_data)

        for q in questions_data:
            Question.objects.create(exam=exam, **q)

        return exam



class ExamSubmissionAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.CharField()



class StudentAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = StudentAnswer
        fields = ['id', 'question', 'question_text','answer', 'is_correct']

class StudentExamSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True) 
    student_name = serializers.CharField(source='student.user.username', read_only=True)
    class Meta:
        model = StudentExam
        fields = ['id', 'exam', 'exam_title', 'marks','student_name',  'submitted_at', 'answers']

class ExamSubmissionSerializer(serializers.Serializer):
    answers = ExamSubmissionAnswerSerializer(many=True)

    def validate_answers(self, value):
        if len(value) != 5:
            raise serializers.ValidationError("You must answer exactly 5 questions.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        exam = self.context['exam']
        student = Student.objects.get(user=user)

        
        if StudentExam.objects.filter(student=student, exam=exam).exists():
            raise serializers.ValidationError("You have already submitted this exam.")

      
        student_exam = StudentExam.objects.create(student=student, exam=exam)
        score = 0

        for ans in validated_data['answers']:
            question_id = ans.get('question_id')
            answer = ans.get('answer')

            try:
                question = Question.objects.get(id=question_id, exam=exam)
            except Question.DoesNotExist:
                raise serializers.ValidationError(
                    f"Question ID {question_id} does not belong to this exam."
                )

            correct_answer = getattr(question, f"option{question.correct_option}")
            is_correct = question.correct_option == answer   

            if is_correct:
                score += 1

            StudentAnswer.objects.create(
                student_exam=student_exam,
                question=question,
                answer=answer,
                is_correct=is_correct
            )

        student_exam.marks = score
        student_exam.save()
        return student_exam
