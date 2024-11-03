from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
import os

class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    class Meta:
        ordering = ['code']
    def __str__(self):
        return self.code

class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    register_number = models.CharField(max_length=20, unique=True)
    def __str__(self):
        return self.user.username
    class Meta:
        ordering = ['user__username']
    
class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    section = models.CharField(max_length=10)
    year_of_join = models.PositiveIntegerField()
    year_of_exit = models.PositiveIntegerField()
    course_id = models.CharField(max_length=10, unique=True, blank=True)
    def __str__(self):
        return self.course_id
    def save(self, *args, **kwargs):
        self.course_id = f"{self.department}{str(self.year_of_join)[-2:]}{self.section}"
        super(Course, self).save(*args, **kwargs)
    class Meta:
        ordering = ['course_id']
    
class Class(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()  
    coordinator = models.ForeignKey(Staff, on_delete=models.CASCADE)
    class_id = models.CharField(max_length=10, unique=True, blank=True)
    def __str__(self):
        return self.class_id
    def save(self, *args, **kwargs):
        self.class_id = f"{self.course}{str(self.semester)}"
        super(Class, self).save(*args, **kwargs)
    class Meta:
        ordering = ['-class_id']

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    register_number = models.CharField(max_length=20, unique=True)
    class_attending = models.ForeignKey(Class, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    transportation =  models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    mentor = models.ForeignKey(Staff, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.username
    def save(self, *args, **kwargs):
        self.user.username = f"{self.class_attending.course}{self.register_number[-3:]}"
        super(User, self.user).save(*args, **kwargs)
        super(Student, self).save(*args, **kwargs)
    class Meta:
        ordering = ['register_number']

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    def __str__(self):
        return self.user.username
    def save(self, *args, **kwargs):
        self.user.username = f"{self.student.user.username}p"
        super(User, self.user).save(*args, **kwargs)
        super(Parent, self).save(*args, **kwargs)
    class Meta:
        ordering = ['user']


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    credit = models.PositiveIntegerField()
    class_related = models.ForeignKey(Class, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.name}-{self.staff}"
    class Meta:
        unique_together = ['code', 'class_related']
        ordering = ['code']


class Exam(models.Model):
    name = models.CharField(max_length=100)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    def __str__(self):
        return  str(self.subject.name) + "-" + str(self.subject.class_related)
    class Meta:
        ordering = ['subject__class_related', 'name']
    
class Result(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    class_related = models.ForeignKey(Class, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    marks = models.PositiveIntegerField(null=True,blank=True)
    grade = models.CharField(max_length=10, null=True,blank=True)
    grade_points = models.PositiveIntegerField(null=True,blank=True)
    def __str__(self):
        return f"{self.exam.name}-{self.exam.subject.code}-{self.student}"
    class Meta:
        unique_together = ['exam', 'class_related', 'student']
        ordering = ['exam']
    
class Holiday(models.Model):
    class_related = models.ForeignKey(Class, on_delete=models.CASCADE)
    date=models.DateField()
    description = models.CharField(max_length=200, blank=True)
    def __str__(self):
        return f"{self.date}-{self.description}"
    class Meta:
        unique_together = ['class_related', 'date']
        ordering = ['date', 'class_related']
    
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_related = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    present_status = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.student}-{self.present_status}"
    class Meta:
        unique_together = ['date', 'class_related','student']
        ordering = ['-date', 'student__register_number']
    
class TimeTable(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()
    def __str__(self):
        return f"{self.subject.name}-{self.day}"
    class Meta:
        unique_together = ['subject', 'day','start_time']
        ordering = ['day', 'start_time']

class Note(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    class Meta:
        unique_together = ['subject', 'file']
        ordering = ['subject']

@receiver(pre_delete, sender=Note)
def delete_note_file(sender, instance, **kwargs):
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)