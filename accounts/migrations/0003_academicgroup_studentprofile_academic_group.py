
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_course_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='accounts.department')),
            ],
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='academic_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='accounts.academicgroup'),
        ),
    ]
