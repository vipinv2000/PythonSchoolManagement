from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from core.models import Exam, Question, Teacher
from .models import User, Teacher, Student, StudentExam, StudentAnswer
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
        fields = ['id', 'username', 'email', 'password', 'role', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

       
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'employee_id', 'phone_number',
            'subject_specialization', 'date_of_joining', 'status'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['role'] = 'teacher'
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
            user_serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        return instance


class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    assigned_teacher = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        required=False,
        allow_null=True
    )
    assigned_teacher_name = serializers.CharField(
        source='assigned_teacher.user.get_full_name', 
        read_only=True
    )

    class Meta:
        model = Student
        fields = [
            'id', 'user', 'roll_number', 'phone_number', 'grade', 
            'class_name', 'date_of_birth', 'admission_date', 'status', 
            'assigned_teacher', 'assigned_teacher_name'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        request_user = self.context['request'].user
        
       
        user_data['role'] = 'student'
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
       
        if request_user.role == 'teacher' and 'assigned_teacher' not in validated_data:
            try:
                teacher = Teacher.objects.get(user=request_user)
                validated_data['assigned_teacher'] = teacher
            except Teacher.DoesNotExist:
                raise serializers.ValidationError("Teacher profile not found for the current user.")

        student = Student.objects.create(user=user, **validated_data)
        return student

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        request_user = self.context['request'].user

       
        if request_user.role != 'admin' and 'assigned_teacher' in validated_data:
            validated_data.pop('assigned_teacher')

       
        if user_data:
            user_serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

      
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class TeacherSelfUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    
    class Meta:
        model = Teacher
        fields = ['first_name', 'last_name', 'email', 'phone_number']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

       
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option'
        ]


class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']


class TeacherMiniSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'employee_id']


class ExamSerializer(serializers.ModelSerializer):
    teacher = TeacherMiniSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        required=False
    )
    questions = QuestionSerializer(many=True, write_only=True, required=True)
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'subject', 'target_class', 'teacher', 'teacher_id', 
            'questions', 'questions_count', 'created_at'
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()

    def validate_questions(self, value):
        if len(value) != 5:
            raise serializers.ValidationError("Each exam must contain exactly 5 questions.")
        return value

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        request_user = self.context['request'].user

       
        if request_user.role == 'teacher' and 'teacher' not in validated_data:
            try:
                teacher = Teacher.objects.get(user=request_user)
                validated_data['teacher'] = teacher
            except Teacher.DoesNotExist:
                raise serializers.ValidationError("Teacher profile not found.")

        validated_data['created_by'] = request_user
        exam = Exam.objects.create(**validated_data)

       
        for q_data in questions_data:
            Question.objects.create(exam=exam, **q_data)

        return exam

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        
       
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

      
        if questions_data is not None:
            
            instance.questions.all().delete()
           
            for q_data in questions_data:
                Question.objects.create(exam=instance, **q_data)

        return instance


class ExamSubmissionAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.CharField()


class StudentAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = StudentAnswer
        fields = ['id', 'question', 'question_text', 'answer', 'is_correct']


class StudentExamSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    exam_subject = serializers.CharField(source='exam.subject', read_only=True)
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    student_roll = serializers.CharField(source='student.roll_number', read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = StudentExam
        fields = [
            'id', 'exam', 'exam_title', 'exam_subject', 'student_name', 
            'student_roll', 'marks', 'total_questions', 'submitted_at', 'answers'
        ]

    def get_total_questions(self, obj):
        return obj.exam.questions.count()


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
        
        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            raise serializers.ValidationError("Student profile not found.")

      
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