from django import forms

from .models import AcademicGroup, Course, Department


class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        if 'department' in self.fields:
            self.fields['department'].empty_label = 'Выберите факультет'


class DepartmentForm(StyledForm):
    class Meta:
        model = Department
        fields = ['name']
        labels = {'name': 'Название'}


class AcademicGroupForm(StyledForm):
    class Meta:
        model = AcademicGroup
        fields = ['name', 'department']
        labels = {'name': 'Название', 'department': 'Факультет'}


class CourseForm(StyledForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'department']
        labels = {'title': 'Название', 'description': 'Описание', 'department': 'Факультет'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}
