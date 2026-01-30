from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from semester.models import Assessment, Course, Semester
from ui.forms_academic import AssessmentForm, CourseForm, SemesterForm
from ui.services_academic import build_course_progress


@login_required(login_url="/login/")
def semester_list_view(request):
    semesters = Semester.objects.filter(user=request.user).order_by("-start_date")
    return render(request, "ui/semester/semester_list.html", {"semesters": semesters})


@login_required(login_url="/login/")
def semester_create_view(request):
    if request.method == "POST":
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save(commit=False)
            semester.user = request.user
            semester.save()
            messages.success(request, _("Semestre criado com sucesso."))
            return redirect("ui-semester-detail", pk=semester.pk)
    else:
        form = SemesterForm()
    return render(request, "ui/semester/semester_form.html", {"form": form, "mode": "create"})


@login_required(login_url="/login/")
def semester_detail_view(request, pk: int):
    semester = get_object_or_404(Semester, pk=pk, user=request.user)
    courses = semester.courses.all().order_by("title")
    return render(
        request,
        "ui/semester/semester_detail.html",
        {"semester": semester, "courses": courses},
    )


@login_required(login_url="/login/")
def semester_update_view(request, pk: int):
    semester = get_object_or_404(Semester, pk=pk, user=request.user)
    if request.method == "POST":
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, _("Semestre atualizado com sucesso."))
            return redirect("ui-semester-detail", pk=semester.pk)
    else:
        form = SemesterForm(instance=semester)
    return render(
        request,
        "ui/semester/semester_form.html",
        {"form": form, "semester": semester, "mode": "edit"},
    )


@login_required(login_url="/login/")
def semester_delete_view(request, pk: int):
    semester = get_object_or_404(Semester, pk=pk, user=request.user)
    if request.method == "POST":
        semester.delete()
        messages.success(request, _("Semestre excluido com sucesso."))
        return redirect("ui-semester-list")
    return render(
        request,
        "ui/semester/semester_confirm_delete.html",
        {"semester": semester},
    )


@login_required(login_url="/login/")
def course_create_view(request, sem_id: int):
    semester = get_object_or_404(Semester, pk=sem_id, user=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.semester = semester
            course.save()
            messages.success(request, _("Disciplina criada com sucesso."))
            return redirect("ui-course-detail", pk=course.pk)
    else:
        form = CourseForm()
    return render(
        request,
        "ui/course/course_form.html",
        {"form": form, "semester": semester, "mode": "create"},
    )


@login_required(login_url="/login/")
def course_detail_view(request, pk: int):
    course = get_object_or_404(Course, pk=pk, semester__user=request.user)
    assessments = course.assessments.all().order_by("-date", "-created_at")
    progress = build_course_progress(course)
    return render(
        request,
        "ui/course/course_detail.html",
        {"course": course, "assessments": assessments, "progress": progress},
    )


@login_required(login_url="/login/")
def course_update_view(request, pk: int):
    course = get_object_or_404(Course, pk=pk, semester__user=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, _("Disciplina atualizada com sucesso."))
            return redirect("ui-course-detail", pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(
        request,
        "ui/course/course_form.html",
        {"form": form, "course": course, "semester": course.semester, "mode": "edit"},
    )


@login_required(login_url="/login/")
def course_delete_view(request, pk: int):
    course = get_object_or_404(Course, pk=pk, semester__user=request.user)
    if request.method == "POST":
        semester_id = course.semester_id
        course.delete()
        messages.success(request, _("Disciplina excluida com sucesso."))
        return redirect("ui-semester-detail", pk=semester_id)
    return render(
        request,
        "ui/course/course_confirm_delete.html",
        {"course": course},
    )


@login_required(login_url="/login/")
def assessment_create_view(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id, semester__user=request.user)
    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.course = course
            assessment.save()
            messages.success(request, _("Avaliacao criada com sucesso."))
            return redirect("ui-course-detail", pk=course.pk)
    else:
        form = AssessmentForm()
    return render(
        request,
        "ui/assessment/assessment_form.html",
        {"form": form, "course": course, "mode": "create"},
    )


@login_required(login_url="/login/")
def assessment_update_view(request, pk: int):
    assessment = get_object_or_404(Assessment, pk=pk, course__semester__user=request.user)
    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request, _("Avaliacao atualizada com sucesso."))
            return redirect("ui-course-detail", pk=assessment.course_id)
    else:
        form = AssessmentForm(instance=assessment)
    return render(
        request,
        "ui/assessment/assessment_form.html",
        {"form": form, "course": assessment.course, "assessment": assessment, "mode": "edit"},
    )


@login_required(login_url="/login/")
def assessment_delete_view(request, pk: int):
    assessment = get_object_or_404(Assessment, pk=pk, course__semester__user=request.user)
    if request.method == "POST":
        course_id = assessment.course_id
        assessment.delete()
        messages.success(request, _("Avaliacao excluida com sucesso."))
        return redirect("ui-course-detail", pk=course_id)
    return render(
        request,
        "ui/assessment/assessment_confirm_delete.html",
        {"assessment": assessment, "course": assessment.course},
    )
