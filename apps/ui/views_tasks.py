from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from planner.models import Task
from ui.forms_tasks import TaskForm
from utils.constants import TASK_DONE, TASK_DOING, TASK_TODO


@login_required(login_url="/login/")
def task_list_view(request):
    tasks = Task.objects.filter(user=request.user)
    status_filter = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()

    if status_filter in {TASK_TODO, TASK_DOING, TASK_DONE}:
        tasks = tasks.filter(status=status_filter)
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))

    tasks = tasks.order_by("due_date")

    return render(
        request,
        "ui/tasks/task_list.html",
        {
            "tasks": tasks,
            "status_filter": status_filter,
            "query": query,
        },
    )


@login_required(login_url="/login/")
def task_create_view(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, _("Tarefa criada com sucesso."))
            return redirect("ui-task-detail", pk=task.pk)
    else:
        form = TaskForm()
    return render(request, "ui/tasks/task_form.html", {"form": form, "mode": "create"})


@login_required(login_url="/login/")
def task_detail_view(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    return render(request, "ui/tasks/task_detail.html", {"task": task})


@login_required(login_url="/login/")
def task_update_view(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, _("Tarefa atualizada com sucesso."))
            return redirect("ui-task-detail", pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, "ui/tasks/task_form.html", {"form": form, "mode": "edit", "task": task})


@login_required(login_url="/login/")
def task_delete_view(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == "POST":
        task.delete()
        messages.success(request, _("Tarefa excluida com sucesso."))
        return redirect("ui-task-list")
    return render(request, "ui/tasks/task_confirm_delete.html", {"task": task})
