# Generated by Django 5.2.4 on 2025-07-19 11:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_exam_target_class_student_class_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='student',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='last_name',
        ),
    ]
