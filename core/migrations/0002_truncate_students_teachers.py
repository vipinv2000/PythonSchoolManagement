from django.db import migrations
import logging

logger = logging.getLogger(__name__)

def truncate_students_and_teachers_users(apps, schema_editor):
    User = apps.get_model('core', 'User')
    Student = apps.get_model('core', 'Student')
    Teacher = apps.get_model('core', 'Teacher')

    logger.info("Deleting all Student records...")
    Student.objects.all().delete()

    logger.info("Deleting all Teacher records...")
    Teacher.objects.all().delete()

    logger.info("Deleting all non-admin Users...")
    User.objects.exclude(role='admin').delete()

def reverse_truncate_students_and_teachers_users(apps, schema_editor):
    logger.warning("Reverse for truncate not implemented.")

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            truncate_students_and_teachers_users,
            reverse_code=reverse_truncate_students_and_teachers_users,
        ),
    ]
