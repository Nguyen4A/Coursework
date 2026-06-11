from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ShelfLifeRuleForm
from .models import ShelfLifeRule


@login_required
def rule_list(request):
    query = request.GET.get("q", "").strip()
    rules = ShelfLifeRule.objects.filter(Q(owner=request.user) | Q(owner__isnull=True), is_active=True)
    if query:
        rules = rules.filter(Q(product_name__icontains=query) | Q(tags__icontains=query) | Q(category__icontains=query))
    return render(request, "knowledge/rule_list.html", {"rules": rules, "query": query})


@login_required
def rule_create(request):
    if request.method == "POST":
        form = ShelfLifeRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.owner = request.user
            rule.save()
            messages.success(request, "Правило добавлено.")
            return redirect("knowledge:rule_list")
    else:
        form = ShelfLifeRuleForm()
    return render(request, "knowledge/rule_form.html", {"form": form, "title": "Добавить правило"})


@login_required
def rule_update(request, pk):
    rule = get_object_or_404(ShelfLifeRule, pk=pk, owner=request.user)
    if request.method == "POST":
        form = ShelfLifeRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, "Правило обновлено.")
            return redirect("knowledge:rule_list")
    else:
        form = ShelfLifeRuleForm(instance=rule)
    return render(request, "knowledge/rule_form.html", {"form": form, "title": "Редактировать правило"})


@login_required
def rule_delete(request, pk):
    rule = get_object_or_404(ShelfLifeRule, pk=pk, owner=request.user)
    if request.method == "POST":
        rule.delete()
        messages.success(request, "Правило удалено.")
        return redirect("knowledge:rule_list")
    return render(request, "knowledge/rule_confirm_delete.html", {"rule": rule})
