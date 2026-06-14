from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from knowledge.services import ShelfLifeService

from .forms import ProductForm
from .models import Product
from .services import ProductPriorityService, ProductUsageService, RecipeSuggestionService, WasteStatsService


@login_required
def product_list(request):
    status_filter = request.GET.get("status", "all")
    sort = request.GET.get("sort", "")
    products = Product.objects.filter(user=request.user).select_related("category")
    if status_filter in {Product.STATUS_ACTIVE, Product.STATUS_EXPIRING_SOON, Product.STATUS_EXPIRED, Product.STATUS_NEEDS_REVIEW}:
        products = products.filter(status=status_filter)
    priority_service = ProductPriorityService()
    if sort == "priority":
        priorities = priority_service.rank(products)
        products = [priority.product for priority in priorities]
        for priority in priorities:
            priority.product.priority_score = priority.score
            priority.product.priority_reasons = priority.reasons
    else:
        products = list(products)
        for product in products:
            priority = priority_service.evaluate(product)
            product.priority_score = priority.score
            product.priority_reasons = priority.reasons
    return render(request, "pantry/product_list.html", {"products": products, "status_filter": status_filter, "sort": sort})


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            if product.shelf_life_days is None:
                suggestion = ShelfLifeService(request.user).suggest(product.name)
                if suggestion:
                    product.shelf_life_days = suggestion.days
                    product.comment = (product.comment + "\n" if product.comment else "") + f"Срок предложен по правилу: {suggestion.rule_name}"
            product.save()
            messages.success(request, "Продукт добавлен.")
            return redirect("pantry:product_list")
    else:
        form = ProductForm(initial={"source": Product.SOURCE_MANUAL})
    return render(request, "pantry/product_form.html", {"form": form, "title": "Добавить продукт"})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Продукт обновлен.")
            return redirect("pantry:product_list")
    else:
        form = ProductForm(instance=product)
    return render(request, "pantry/product_form.html", {"form": form, "title": "Редактировать продукт"})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Продукт удален.")
        return redirect("pantry:product_list")
    return render(request, "pantry/product_confirm_delete.html", {"product": product})


@login_required
def product_mark_used(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    product = get_object_or_404(Product, pk=pk, user=request.user)
    ProductUsageService().mark(product, "used")
    messages.success(request, "Продукт отмечен как использованный.")
    return redirect("pantry:product_list")


@login_required
def product_mark_wasted(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    product = get_object_or_404(Product, pk=pk, user=request.user)
    ProductUsageService().mark(product, "wasted")
    messages.success(request, "Продукт отмечен как выброшенный.")
    return redirect("pantry:product_list")


@login_required
def recipe_ideas(request):
    suggestions = RecipeSuggestionService(request.user).suggest()
    return render(request, "pantry/recipe_ideas.html", {"suggestions": suggestions})


@login_required
def waste_stats(request):
    stats = WasteStatsService(request.user).build()
    return render(request, "pantry/waste_stats.html", stats)
