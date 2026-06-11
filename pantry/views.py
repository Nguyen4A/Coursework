from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from knowledge.services import ShelfLifeService

from .forms import ProductForm
from .models import Product


@login_required
def product_list(request):
    status_filter = request.GET.get("status", "all")
    products = Product.objects.filter(user=request.user).select_related("category")
    if status_filter in {Product.STATUS_ACTIVE, Product.STATUS_EXPIRING_SOON, Product.STATUS_EXPIRED, Product.STATUS_NEEDS_REVIEW}:
        products = products.filter(status=status_filter)
    return render(request, "pantry/product_list.html", {"products": products, "status_filter": status_filter})


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
