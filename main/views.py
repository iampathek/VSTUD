from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from . import models
import calendar
from datetime import datetime, timedelta, date
from .templatetags.custom_filters import calculate_attendance, weekly_analysis, calculate_leaves, leaves_availed, month_attendance
from django.core.mail import send_mail
from django.conf import settings
import random,string
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash


# Basic
def is_staff(user):
    try:
        staff = models.Staff.objects.get(user=user)
        return True
    except:
        return False
    
def is_student(user):
    try:
        student = models.Student.objects.get(user=user)
        return True
    except:
        return False

def is_parent(user):
    try:
        parent = models.Parent.objects.get(user=user)
        print(parent)
        return True
    except:
        return False

@login_required
def home(request):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        return redirect("staff-attendance", class_attending_list[0])
    elif is_student(user):
        student = models.Student.objects.get(user=user)
        return redirect("attendance", student.class_attending.class_id)
    elif is_parent(user):
        parent = models.Parent.objects.get(user=user)
        return redirect("attendance", parent.student.class_attending.class_id)

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST["password"]
        user = authenticate(username=username, password=password)
        if user is not None:
                try:
                    staff = models.Staff.objects.get(user=user)
                    subjects = models.Subject.objects.filter(staff=staff)
                    class_attending_list = []
                    for subject in subjects:
                        class_attending = subject.class_related
                        if class_attending not in class_attending_list:
                            class_attending_list.append(class_attending)
                    login(request, user)
                    return redirect("staff-attendance", class_attending_list[0].class_id)
                except:
                    print("failed to fetch staff in user_login")
                try:
                    student = models.Student.objects.get(user=user)
                    login(request, user)
                    return redirect("attendance", student.user.username)
                except:
                    print("failed to fetch student in user_login")
                try:
                    parent = models.Parent.objects.get(user=user)
                    login(request, user)
                    print(parent.student.user.username)
                    return redirect("attendance", parent.student.user.username)
                except:
                    print("failed to fetch parent in user_login")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")
    return render(request, "common/login.html")

def user_logout(request):
    logout(request)
    return redirect("login")

# Class
@login_required
def attendance(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)

    month = datetime.now().month
    year = datetime.now().year
    month_percent = month_attendance(student=student, start_date=datetime(year, month, 1).date())
    sem_percent = calculate_attendance(student=student)
    weekly_report = weekly_analysis(student=student)
    context = {
        "user":user,
        "sem_percent" : sem_percent,
        "month_percent" : month_percent,
        "student" : student,
        "staff" : staff,
        "parent" : parent,
        "weekly_report" : weekly_report,
        "leaves": calculate_leaves(student=student),
        "leaves_availed": leaves_availed(student=student)
    }
    return render(request, "student/class/attendance.html", context)

@login_required
def staff_attendance(request, class_id):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    class_related = models.Class.objects.get(class_id=class_id)
    context = {
        "user":user,
        "staff":staff,
        "date" : date.today(),
        "classes":class_attending_list,
        "class_id":class_id,
    }
    class_absent_students = []
    class_present_students = []
    students = models.Student.objects.filter(class_attending=class_related)
    for student in students:
        try:
            student_attendance = models.Attendance.objects.get(student=student, class_related=class_attending, date=date.today())
        except:
            student_attendance = None
        if student_attendance!=None and student_attendance.present_status:
            class_present_students.append(student)
        elif student_attendance!=None and student_attendance.present_status==False:
            class_absent_students.append(student)
        context[student.user.username] = calculate_attendance(student=student)
    try:
        holiday = models.Holiday.objects.get(date=date.today(), class_related__class_id=class_id)
    except:
        holiday = False
    context["present"] = len(class_present_students)
    context["absent"] = len(class_absent_students)
    context["strength"] = len(class_absent_students) + len(class_present_students)
    context["absentees"] = class_absent_students
    context["holiday"] = holiday
    return render(request, "staff/class/attendance.html", context)

@login_required
def timetable(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
        
    holidays = models.Holiday.objects.filter(class_related=student.class_attending)
    timetable = models.TimeTable.objects.filter(subject__class_related=student.class_attending)
    sem_start_date = student.class_attending.start_date
    sem_end_date = student.class_attending.end_date
    # Academic Calendar
    cal = {}
    date_pointer = sem_start_date
    while date_pointer <= sem_end_date:
        year = date_pointer.year
        month = date_pointer.month
        month_name = calendar.month_name[month]
        if month_name not in cal:
            cal[month_name] = calendar.monthcalendar(year, month)
        date_pointer += timedelta(days=1)
    _holidays = {}
    for holiday in holidays:
        month = holiday.date.month
        if month not in _holidays:
            _holidays[month] = []
        else:
            _holidays[month].append(holiday.date.day)
    # Timetable
    _timetable = {}
    for each in timetable:
        day = each.day
        if day not in _timetable:
            _timetable[day] = []
        _timetable[day].append(each)
    context = {
        "user":user,
        "student":student, 
        "staff":staff,
        "parent":parent,
        "cal":cal, 
        "holidays":_holidays, 
        "timetable":_timetable
        }
    return render(request, "student/class/timetable.html", context)

@login_required
def staff_timetable(request, class_id):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list and class_attending.class_id!=class_id:
            class_attending_list.append(class_attending)
    class_related = models.Class.objects.get(class_id=class_id)
    holidays = models.Holiday.objects.filter(class_related=class_related)
    timetable = models.TimeTable.objects.filter(subject__class_related=class_related)
    sem_start_date = class_related.start_date
    sem_end_date = class_related.end_date
    # Academic Calendar
    cal = {}
    date_pointer = sem_start_date
    while date_pointer <= sem_end_date:
        year = date_pointer.year
        month = date_pointer.month
        month_name = calendar.month_name[month]
        if month_name not in cal:
            cal[month_name] = calendar.monthcalendar(year, month)
        date_pointer += timedelta(days=1)
    _holidays = {}
    for holiday in holidays:
        month = holiday.date.month
        if month not in _holidays:
            _holidays[month] = []
        else:
            _holidays[month].append(holiday.date.day)
    # Timetable
    _timetable = {}
    for each in timetable:
        day = each.day
        if day not in _timetable:
            _timetable[day] = []
        _timetable[day].append(each)
    context ={
        "staff":staff,
        "user":user,
        "class_id":class_id,
        "classes":class_attending_list,
        "cal":cal, 
        "holidays":_holidays, 
        "timetable":_timetable,
    }
    return render(request, "staff/class/staff-timetable.html", context)

@login_required
def notes(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    subjects = models.Subject.objects.filter(class_related=student.class_attending)
    _notes = []
    for subject in subjects:
        _notes.append(models.Note.objects.filter(subject=subject))
    for subject_note in _notes:
        for note in subject_note:
            print(note.title)
    context = {
        "user":user,
        "student":student,
        "staff":staff,
        "parent":parent,
        "subjects":subjects,
        "all_notes":_notes,
    }
    print(_notes[4])
    return render(request, "student/class/notes.html", context) 

@login_required
def staff_notes(request, class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    subject = models.Subject.objects.filter(staff=staff, class_related__class_id=class_id)[0]
    subject_notes = models.Note.objects.filter(subject=subject)
    context = {
        'user': user,
        'staff': staff,
        "class_id":class_id,
        "classes": class_attending_list,
        'subject': subject,
        "subject_notes":subject_notes,
    }

    return render(request, "staff/class/staff-notes.html", context)

    
# Result
@login_required
def ia_result(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    ia1 = models.Result.objects.filter(exam__name="ia1", student=student, class_related=student.class_attending)
    ia2 = models.Result.objects.filter(exam__name="ia2", student=student, class_related=student.class_attending)
    ia3 = models.Result.objects.filter(exam__name="ia3", student=student, class_related=student.class_attending)
    context = {
        "user":user,
        "student":student,
        "ia1":ia1,
        "ia2":ia2,
        "ia3":ia3
    }
    return render(request, "student/result/ia.html", context)

@login_required
def staff_ia_result(request, class_id=None):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    subject = models.Subject.objects.filter(class_related__class_id = class_id, staff=staff)[0]
    ia1_results = models.Result.objects.filter(class_related__class_id=class_id, exam__name = 'ia1', exam__subject = subject)
    ia2_results = models.Result.objects.filter(class_related__class_id=class_id, exam__name = 'ia2', exam__subject = subject)
    ia3_results = models.Result.objects.filter(class_related__class_id=class_id, exam__name = 'ia3', exam__subject = subject)
    context = {
        "user":user,
        "staff":staff,
        "classes":class_attending_list,
        "class_id":class_id,
        "ia1_results" : ia1_results,
        "ia2_results" : ia2_results,
        "ia3_results" : ia3_results,
    }
    return render(request, "staff/result/staff-ia.html", context)

@login_required
def model_result(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    model_exam = models.Result.objects.filter(exam__name="model", student=student, class_related=student.class_attending)
    context = {
        "user":user,
        "student":student,
        "model":model_exam,
    }
    return render(request, "student/result/model.html", context)

@login_required
def staff_model_result(request, class_id=None):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    subject = models.Subject.objects.filter(class_related__class_id = class_id, staff=staff)[0]
    model_results = models.Result.objects.filter(class_related__class_id=class_id, exam__name = 'model', exam__subject = subject)
    context = {
        "user":user,
        "staff":staff,
        "classes":class_attending_list,
        "class_id":class_id,
        "model_results" : model_results,
    }
    return render(request, "staff/result/staff-model.html", context)

@login_required
def sem_result(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    semesters_data = []
    for i in range(1,9):
        sem = "semester-"+str(i)
        semesters_data.append(models.Result.objects.filter(exam__name=sem, student=student))
    print(semesters_data)
    context = {
        "user":user,
        "student":student,
        "semesters_data":semesters_data
    }
    return render(request, "student/result/sem.html", context)

@login_required
def staff_sem_result(request, class_id):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    subject = models.Subject.objects.filter(class_related__class_id = class_id, staff=staff)[0]
    semester_results = models.Result.objects.filter(class_related__class_id=class_id, exam__name = 'semester', exam__subject = subject)
    context = {
        "user":user,
        "staff":staff,
        "classes":class_attending_list,
        "class_id":class_id,
        "semester_results" : semester_results,
    }
    return render(request, "staff/result/staff-sem.html", context)

# password reset
def password_reset_form(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Check if passwords match
        if password == confirm_password:
            # Check if the user is authenticated
            if request.user.is_authenticated:
                user = request.user
            else:
                # Get the user email from the mail form
                user_name = mail_form(request, return_email=False)
                try:
                    user = models.User.objects.get(username = user_name)
                except User.DoesNotExist:
                    # User does not exist, redirect to mail form
                    return redirect("mail-form")  
                
            # Update the user's password
            user.set_password(password)
            user.save()

            # Update the user's session to prevent them from being logged out
            # if not request.user.is_authenticated:
            #     update_session_auth_hash(request, user)

            # Redirect to logout page
            return redirect("logout")

        else:
            # Passwords do not match, provide feedback to user
            # For example, you can add an error message to the context
            messages.error("The password and confirm password should be the same.")
            
    # Render the password reset form
    return render(request, "common/password-reset-form.html")
def check_mail_notification(request):
    user = request.user
    user_email = None
    token = None
    if request.user.is_authenticated:
        user_email = request.user.email
    else:
        user_email = mail_form(request, return_email=True)
    user = models.User.objects.get(email = user_email)
    print(user)
    token = default_token_generator.make_token(user)
    # reset_url = request.build_absolute_uri(reverse('password_reset_confirm', kwargs={'uidb64': user.pk, 'token': token}))
    reset_form_url = request.build_absolute_uri(reverse('password-reset-form'))

    send_mail(
        'Password Reset',
        f'Click the following link to reset your password: {reset_form_url}?token={token}',
        settings.EMAIL_HOST_USER,  # Sender email address
        [user_email],  # Recipient email address
        fail_silently=False,
    )
    context = {
        'user_email': user_email
    }
    return render(request, "common/check-mail-notification.html", context)

def mail_form(request, return_email=False):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_name = request.POST.get('username')
        if return_email:
            return email
        else:
            return user_name
    return render(request, "common/mail-form.html")

# Forms
@login_required
def add_attendance_form(request, class_id, _date):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)

    class_related = models.Class.objects.get(class_id=class_id)
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        register_number = request.POST.get('reg_no')
        _date = request.POST.get('date')
        present_status = request.POST.get('present-status')
        class_related = models.Class.objects.get(class_id=class_id)
        student = models.Student.objects.get(register_number=register_number)
        try:
            already_attendance_taken = models.Attendance.objects.get(student=student, class_related=class_related, date=_date)
        except:
            already_attendance_taken = False
        if already_attendance_taken==False:
            models.Attendance.objects.create(student=student, class_related=class_related, date=_date, present_status=present_status)

        if 'save_and_next' in request.POST:
            return redirect('add-attendance-form', class_id, _date)
        elif 'save_and_exit' in request.POST:
            return redirect("staff-attendance")
    students = models.Student.objects.filter(class_attending = class_related)
    _student = None
    for student in students:
        try:
            _attendance = models.Attendance.objects.get(student=student, date=_date)
        except:
            _attendance = None
        if _attendance is not None:
            continue
        else:
            _student = student
            break

    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        'class': class_related,
        'class_id':class_id,
        'date': _date,
        'student':_student,
    }

   
    if _student is None:
        return redirect('staff-attendance' , class_id)
    return render(request, "staff/admin/add-attendance.html", context)

def add_notes(request, class_id = None):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    class_related = models.Class.objects.get(class_id=class_id)

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        note_name = request.POST.get('note_name')
        note_file = request.POST.get('note_file')
        subject_code = request.POST.get('subject_name')
        subject = models.Subject.objects.get(code=subject_code, class_related=class_related)
        models.Note.objects.create(
            title = note_name,
            file = note_file,  
            subject = subject,  
        )
        if 'submit' in request.POST:
         return redirect("staff-notes", class_id)
    
    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        'class': class_related,
        'class_id':class_id,
    }

    return render(request, "staff/admin/add-notes.html", context)

@login_required
def add_timetable_form(request, class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    mentors = models.Staff.objects.all()
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    if request.method == 'POST':
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        subject_code = request.POST.get('period')
        subject = get_object_or_404(models.Subject, code=subject_code, class_related__class_id=class_id)     
        models.TimeTable.objects.create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            subject=subject
        )
    all_subjects = models.Subject.objects.filter(class_related__class_id=class_id)
    context = {
    'user': user,
    'staff': staff,
    'subjects': all_subjects,
    "classes": class_attending_list,
    "class_id":class_id,
}
    if 'save_and_next' in request.POST:
        return redirect("add-timetable-form", class_id)
    elif 'save_and_exit' in request.POST:
        return redirect("staff-attendance", class_id)
    return render(request, "staff/admin/add-timetable.html", context)

@login_required
def add_student(request, class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    mentors = models.Staff.objects.all()
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)

    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        "class_id":class_id,
        "mentors":mentors,
    }
    if request.method == 'POST':
        first_name = request.POST.get("first-name")
        last_name = request.POST.get("last-name")
        email = request.POST.get("email")
        register_no = request.POST.get("register-number")
        class_attending = class_id
        dob = request.POST.get("dob")
        gender = request.POST.get("gender")
        transport = request.POST.get("transport")
        phone_no = request.POST.get("phone-no")
        mentor = request.POST.get("mentor")
        username =f"{class_attending[:5]}{register_no[-3:]}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        staff_user = models.User.objects.get(username=mentor)
        class_attending = models.Class.objects.get(class_id=class_attending)
        mentor=models.Staff.objects.get(user=staff_user)
        user = User.objects.create_user(first_name=first_name,last_name=last_name,email=email,username=username , password=password)
        user.save()
        message = f'''
Hello {first_name}, Welcome To VSTUD.
We are from Velammal Institute Of Technology!!!
Username : {username}
password : {password}

Disclaimer : **Dont forget to change your password on website**
'''
        send_mail(
                'VSTUD',message,'settings.EMAIL_HOST_USER',[email],fail_silently=False

            )        
        if user:
            student = models.Student(user=user, register_number=register_no,class_attending=class_attending,date_of_birth=dob,gender=gender,phone=phone_no,mentor=mentor, transportation=transport)
            student.save()
            return redirect('admin-users', class_id)
    
    return render(request , "staff/admin/add-student.html", context)

@login_required
def add_parent(request):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    students = models.Student.objects.all
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    class_id = class_attending_list[0]
    context = {
        'user': user,
        'staff': staff,
        "classes":class_attending_list,
        'subjects': subjects,
        "students":students,  
        "class_id":class_id,
    }
    if request.method == 'POST':
        first_name = request.POST.get("first-name")
        last_name = request.POST.get("last-name")
        email = request.POST.get("email")
        phone_no = request.POST.get("phone-no")
        student_id = request.POST.get("student")
        username =f"{student_id}p"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user = User.objects.create_user(first_name=first_name,last_name=last_name,email=email,username=username,password=password)
        user.save()
        message = f'''
Hello {first_name}, Welcome To VSTUD.
We are from Velammal Institute Of Technology!!!
As a Parent you can view your child's performance in VSTUD website.
Username : {username}
password : {password}

Disclaimer : **Dont forget to change your password on website**
'''
        send_mail(
                'VSTUD',message,'settings.EMAIL_HOST_USER',[email],fail_silently=False
            )        
        if user:
            student = models.Student.objects.get(user__username=student_id)
            print(student)
            parent = models.Parent(user=user,phone=phone_no,student=student)
            parent.save()
            return redirect('admin-users', class_id)
    
    return render(request , "staff/admin/add-parent.html", context)

def add_staff(request, class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        staff_number = request.POST.get('staff_number')
        staff_email = request.POST.get('staff_email')
        staff_reg = request.POST.get('staff_reg')

    
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        new_user = User.objects.create_user(first_name=first_name,last_name=last_name,email=staff_email,username=staff_reg,password=password)
        new_user.is_staff = True
        new_user.save()

        models.Staff.objects.create(
            user = new_user,
            phone = staff_number,    
        )
        if 'save-and-exit' in request.POST:
            return redirect("staff-attendance")
        elif 'next' in request.POST:
            return redirect("add-staff", class_id)
    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        'class_id': class_id,
    }
        
    return render(request, "staff/admin/add-staff.html", context)

def add_holiday(request,class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)

    if request.method == 'POST':
        class_id = request.POST.get("class-related")
        class_related = models.Class.objects.get(class_id = class_id)
        date = request.POST.get('date')
        description = request.POST.get('description')
        print(date)
        print(description)
        models.Holiday.objects.create(
            class_related = class_related,
            date = date,
            description = description,  
        )

        print("---------------")
        if 'save-and-exit' in request.POST:
            return redirect("staff-attendance")
        elif 'next' in request.POST:
            return redirect("add-holiday", class_id)
    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        "class_id": class_id,
    }
    return render(request, "staff/admin/add-holiday.html" ,context)

def add_exam(request, class_id):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    subjects = models.Subject.objects.filter(class_related__class_id=class_id)
    if request.method=="POST":
        name = request.POST.get("exam-name")
        subject_code = request.POST.get("subject")
        date = request.POST.get("exam-date")
        subject = models.Subject.objects.get(code=subject_code, class_related__class_id=class_id)
        models.Exam.objects.create(name=name,subject=subject,date=date)
        return redirect("add-exam", class_id)
    context = {
        'user': user,
        'staff': staff,
        "classes": class_attending_list,
        "class_id":class_attending_list[0],
        "subjects":subjects
    }
    return render(request,"staff/admin/add-exam.html", context)

@login_required
def add_ia(request, class_id, exam):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    return 0

def add_subject(request, class_id):
    user = request.user
    staff = get_object_or_404(models.Staff, user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    staff_members = models.Staff.objects.all()
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)

    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        subject_name = request.POST.get('subject_name')
        subject_code = request.POST.get('subject_code')
        subject_credit = request.POST.get('subject_credit')
        staff_username = request.POST.get('staff')
        class_related = models.Class.objects.get(class_id = class_id)
        staff = models.Staff.objects.get(user__username = staff_username)
        same_subject = models.Subject.objects.filter(code=subject_code, class_related=class_related)
        if len(same_subject)>0:
            messages.error(request, "The subject already exists in the database.")
        else:
            models.Subject.objects.create(
                name = subject_name,
                code = subject_code,
                credit = subject_credit,
                class_related = class_related,
                staff = staff,
            )

            if 'save-and-exit' in request.POST:
                return redirect("staff-attendance", class_id)
            elif 'save-and-next' in request.POST:
                return redirect("add-subject", class_id)
    context = {
        'user': user,
        'staff': staff,
        'subjects': subjects,
        "classes": class_attending_list,
        'staff_members': staff_members,
        'class_id': class_id,
    }
    return render(request, "staff/admin/add-subject.html",context)

@login_required
def add_department(request):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    if request.method=="POST":
        name = request.POST.get("department-name")
        code = request.POST.get("department-code")
        try:
            already_exist = models.Department.objects.get(code=code)
        except:
            models.Department.objects.create(name=name,code=code)

    context = {
        'user': user,
        'staff': staff,
        "classes": class_attending_list,
        "class_id":class_attending_list[0],
    }
    return render(request,"staff/admin/add-department.html", context)

@login_required
def add_course(request):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    departments = models.Department.objects.all()
    if request.method=="POST":
        department_code = request.POST.get("department")
        section = request.POST.get("section")
        year_of_join =request.POST.get("join-year")
        year_of_exit =request.POST.get("exit-year")
        try:
            department = models.Department.objects.get(code=department_code)
            already_exist = models.Course.objects.get(code=department_code , section=section,year_of_join=year_of_join)
        except:
            models.Course.objects.create(department=department,section=section,year_of_join=year_of_join,year_of_exit=year_of_exit)
            return redirect("add-course")
            
    context = {
        'user': user,
        'staff': staff,
        "classes": class_attending_list,
        "class_id":class_attending_list[0],
        "departments":departments,
    }
    return render(request,"staff/admin/add-course.html", context)

@login_required
def add_class(request):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    courses = models.Course.objects.all()
    all_staff = models.Staff.objects.all()
    if request.method=="POST":
        course = request.POST.get("course")
        semester = request.POST.get("semester")
        year = request.POST.get("year")
        sem_start_date = request.POST.get("sem-start-date")
        sem_end_date = request.POST.get("sem-end-date")
        co_ordinator = request.POST.get("coordinator")
        co_ordinator = models.Staff.objects.get(user__username=co_ordinator)
        try:
            course = models.Course.objects.get(course_id=course)
            already_exist = models.Class.objects.get(course=course,semester=semester)
        except:
            models.Class.objects.create(course=course,semester=semester,year=year,start_date=sem_start_date,end_date=sem_end_date,coordinator=co_ordinator)
            return redirect("add-class")
    context = {
        'user': user,
        'staff': staff,
        "classes": class_attending_list,
        "class_id":class_attending_list[0],
        "courses":courses,
        "all_staff":all_staff,
    }
    return render(request,"staff/admin/add-class.html", context)

@login_required
def staff_profile(request):
    user = request.user
    staff = models.Staff.objects.get(user=user)
    subjects = models.Subject.objects.filter(staff=staff)
    class_attending_list = []
    for subject in subjects:
        class_attending = subject.class_related
        if class_attending not in class_attending_list:
            class_attending_list.append(class_attending)
    context = {
        "user":user,
        "staff":staff,
        "classes": class_attending_list,
        "class_id":class_attending_list[0],
    }
    return render(request,"staff/profile.html",context)

@login_required
def profile(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    parent = models.Parent.objects.get(student=student)
    
    context = {
        "user":user,
        "student":student,
        "parent":parent,
        "staff":staff,
    }
    return render(request,"student/profile.html",context)

def student_library(request, student_id):
    user = request.user
    parent=staff=student=None
    if is_parent(user):
        parent = models.Parent.objects.get(user=user)
        student = parent.student
    elif is_staff(user):
        staff = models.Staff.objects.get(user=user)
        student = models.Student.objects.get(user__username=student_id)
    else:
        student = models.Student.objects.get(user=user)
    context = {
        "user":user,
        "student":student,
        "staff":staff,
        "parent":parent,   
    }
    return render(request, "student/library/processing.html", context)

#admin page
@login_required
def admin_attendance(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        _attendance = models.Attendance.objects.filter(class_related__class_id=class_id)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "attendance":_attendance,
            "date": datetime.today().date
        }
        return render(request, "staff/admin/attendance.html", context)
    else:
        return redirect("login")
    
@login_required
def admin_notes(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        notes = models.Note.objects.filter(subject__class_related__class_id = class_id, subject__staff=staff)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "notes":notes,
        }
        return render(request, "staff/admin/notes.html", context)
    else:
        return redirect("login")
    
@login_required
def admin_timetable(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        periods = models.TimeTable.objects.filter(subject__class_related__class_id = class_id)
        holidays = models.Holiday.objects.filter(class_related__class_id = class_id)
        print("----------------", periods)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "periods":periods,
            "holidays":holidays,
        }
        return render(request, "staff/admin/timetable.html", context)
    else:
        return redirect("login")
    
@login_required
def admin_results(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        periods = models.TimeTable.objects.filter(subject__class_related__class_id = class_id)
        ia_results = []
        ia_results += models.Result.objects.filter(exam__subject__class_related__class_id=class_id, exam__subject__staff=staff, exam__name="ia1")
        ia_results += models.Result.objects.filter(exam__subject__class_related__class_id=class_id, exam__subject__staff=staff, exam__name="ia2")
        ia_results += models.Result.objects.filter(exam__subject__class_related__class_id=class_id, exam__subject__staff=staff, exam__name="ia3")
        model_results = models.Result.objects.filter(exam__subject__class_related__class_id=class_id, exam__subject__staff=staff, exam__name="model")
        semester_results = models.Result.objects.filter(exam__subject__class_related__class_id=class_id, exam__subject__staff=staff, exam__name="semester")
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "periods":periods,
            # "results":results,
            "ia_results": ia_results,
            "model_results":model_results,
            "semester_results": semester_results,
        }
        return render(request, "staff/admin/new-results.html", context)
    else:
        return redirect("login")
    
@login_required
def admin_exams(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        periods = models.TimeTable.objects.filter(subject__class_related__class_id = class_id)
        exams = models.Exam.objects.filter(subject__class_related__class_id=class_id)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "periods":periods,
            "exams":exams,
        }
        return render(request, "staff/admin/exams.html", context)
    else:
        return redirect("login")

@login_required    
def admin_users(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        periods = models.TimeTable.objects.filter(subject__class_related__class_id = class_id)
        students = models.Student.objects.filter(class_attending__class_id=class_id)
        all_staff = models.Staff.objects.all()
        parents = models.Parent.objects.filter(student__class_attending__class_id=class_id)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "periods":periods,
            "students": students,
            "parents": parents,
            "staffs": all_staff,
        }
        return render(request, "staff/admin/users.html", context)
    else:
        return redirect("login")
    
@login_required    
def admin_subjects(request, class_id):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        periods = models.TimeTable.objects.filter(subject__class_related__class_id = class_id)
        students = models.Student.objects.filter(class_attending__class_id=class_id)
        all_subjects = models.Subject.objects.filter(class_related__class_id=class_id)
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_id,
            "date": datetime.today().date,
            "periods":periods,
            "students": students,
            "all_subjects":all_subjects,
        }
        return render(request, "staff/admin/subjects.html", context)
    else:
        return redirect("login")
 
@login_required    
def admin_academic_details(request):
    user = request.user
    if is_staff(user):
        staff = models.Staff.objects.get(user=user)
        subjects = models.Subject.objects.filter(staff=staff)
        class_attending_list = []
        for subject in subjects:
            class_attending = subject.class_related
            if class_attending not in class_attending_list:
                class_attending_list.append(class_attending)
        classes = models.Class.objects.all()
        courses  = models.Course.objects.all()
        departments = models.Department.objects.all()
        context = {
            "user":user,
            "staff":staff,
            "classes":class_attending_list,
            "class_id":class_attending_list[0],
            "date": datetime.today().date,
            "classes":classes,
            "courses":courses,
            "departments":departments,
        }
        return render(request, "staff/admin/academic-details.html", context)
    else:
        return redirect("login")
   