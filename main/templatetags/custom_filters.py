from django import template
from .. import models
import calendar
from datetime import datetime, date

register = template.Library()


@register.filter(name='set_student')
def set_student(student):
    global current_user
    current_user = student.user
    return ""

@register.filter(name='check_holiday')
def check_holiday(month,day):
    student = models.Student.objects.get(user=current_user)
    holidays = models.Holiday.objects.filter(class_related=student.class_attending)
    for holiday in holidays:
        holiday_month = calendar.month_name[holiday.date.month]
        holiday_day = holiday.date.day
        if holiday_month==month and  holiday_day==day:
            return True
    return False

@register.filter(name='set_class_id')
def set_class_id(classID):
    global class_id
    class_id = classID
    return ""

@register.filter(name='staff_check_holiday')
def staff_check_holiday(month,day):
    class_related = models.Class.objects.get(class_id=class_id)
    print(class_related)
    holidays = models.Holiday.objects.filter(class_related=class_related)
    for holiday in holidays:
        holiday_month = calendar.month_name[holiday.date.month]
        holiday_day = holiday.date.day
        if holiday_month==month and  holiday_day==day:
            return True
    return False

@register.filter(name='month_attendance')
def month_attendance(student, start_date):
    present_attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending, present_status=True, date__gte=start_date)
    absent_attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending, present_status=False)
    total_days = len(present_attendance)+len(absent_attendance)
    if total_days!=0:
        percent = len(present_attendance)/total_days*100
    else:
        percent = 0
    return int(percent)

@register.filter(name='calculate_attendance')
def calculate_attendance(student):
    present_attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending, present_status=True)
    absent_attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending, present_status=False)
    total_days = len(present_attendance)+len(absent_attendance)
    if total_days!=0:
        percent = len(present_attendance)/total_days*100
    else:
        percent = 0
    return int(percent)

@register.filter(name='calculate_leaves')
def calculate_leaves(student):
    leaves = models.Attendance.objects.filter(student=student, class_related=student.class_attending, present_status = False)
    return len(leaves)

@register.filter(name='class_strength')
def class_strength(class_related):
    students = models.Student.objects.filter(class_attending=class_related)
    return len(students)

@register.filter(name='class_present_count')
def class_present_count(class_related):
    attendance = models.Attendance.objects.filter(class_related=class_related, present_status=True, date=date.today())
    return len(attendance)

@register.filter(name='class_absent_count')
def class_absent_count(class_related):
    attendance = models.Attendance.objects.filter(class_related=class_related, present_status=False, date=date.today())
    return len(attendance)

@register.filter(name='weekly_analysis')
def weekly_analysis(student):
    attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending)
    absent_days = {}
    for day in attendance:
        if day.present_status==False:
            _date = day.date
            _week_name = _date.strftime("%A").lower()
            if _week_name not in absent_days:
                absent_days[_week_name] = 1
            else:
                absent_days[_week_name] += 1
    return absent_days

@register.filter(name='leaves_availed')
def leaves_availed(student):
    attendance = models.Attendance.objects.filter(student=student, class_related=student.class_attending)
    absent_days = {}
    for day in attendance:
        if day.present_status==False:
            _date = day.date
            _week_name = _date.strftime("%A")
            if _week_name not in absent_days:
                absent_days[day] = _week_name
    return absent_days

