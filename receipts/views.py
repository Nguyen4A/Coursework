from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EmailImportSourceForm, ReceiptFileForm, ReceiptItemReviewForm, ReceiptManualTextForm, ReceiptTextForm
from .models import EmailImportSource, Receipt, ReceiptItem
from .services import EmailImportService, OCRService, ReceiptImportService


@login_required
def import_text(request):
    if request.method == "POST":
        form = ReceiptTextForm(request.POST)
        if form.is_valid():
            receipt = ReceiptImportService(request.user).import_text(form.cleaned_data["text"])
            messages.success(request, f"Импортировано позиций: {receipt.items.count()}.")
            return redirect("receipts:detail", pk=receipt.pk)
    else:
        form = ReceiptTextForm()
    return render(request, "receipts/import_text.html", {"form": form})


@login_required
def import_file(request):
    if request.method == "POST":
        form = ReceiptFileForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = Receipt.objects.create(user=request.user, source=Receipt.SOURCE_FILE, file=form.cleaned_data["file"], status="needs_text")
            text = form.cleaned_data.get("recognized_text") or OCRService().extract_text(receipt.file.path)
            if text:
                ReceiptImportService(request.user).import_text(text, source=Receipt.SOURCE_FILE, receipt=receipt)
                messages.success(request, "Файл обработан.")
            else:
                messages.info(request, "Файл сохранен. OCR не подключен, вставьте распознанный текст вручную.")
            return redirect("receipts:detail", pk=receipt.pk)
    else:
        form = ReceiptFileForm()
    return render(request, "receipts/import_file.html", {"form": form})


@login_required
def detail(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk, user=request.user)
    if request.method == "POST":
        form = ReceiptManualTextForm(request.POST)
        if form.is_valid():
            ReceiptImportService(request.user).import_text(form.cleaned_data["text"], source=receipt.source, receipt=receipt)
            messages.success(request, "Текст обработан.")
            return redirect("receipts:detail", pk=receipt.pk)
    else:
        form = ReceiptManualTextForm(initial={"text": receipt.original_text})
    return render(request, "receipts/detail.html", {"receipt": receipt, "form": form})


@login_required
def review_item(request, pk):
    item = get_object_or_404(ReceiptItem.objects.select_related("receipt"), pk=pk, receipt__user=request.user)
    if request.method != "POST":
        return redirect("receipts:detail", pk=item.receipt_id)
    form = ReceiptItemReviewForm(request.POST)
    if form.is_valid():
        importer = ReceiptImportService(request.user)
        if form.cleaned_data["action"] == ReceiptItemReviewForm.ACTION_FOOD:
            importer.confirm_item_as_food(item, form.cleaned_data["category"], form.cleaned_data["keyword"])
            messages.success(request, "Позиция добавлена как продукт, правило сохранено.")
        else:
            importer.confirm_item_as_non_food(item, form.cleaned_data["keyword"])
            messages.success(request, "Позиция отмечена как непищевая, правило сохранено.")
    else:
        messages.error(request, "Не удалось сохранить проверку позиции.")
    return redirect("receipts:detail", pk=item.receipt_id)


@login_required
def email_sources(request):
    sources = EmailImportSource.objects.filter(user=request.user)
    return render(request, "receipts/email_sources.html", {"sources": sources})


@login_required
def email_source_create(request):
    if request.method == "POST":
        form = EmailImportSourceForm(request.POST)
        if form.is_valid():
            source = form.save(commit=False)
            source.user = request.user
            source.save()
            messages.success(request, "Источник почты сохранен.")
            return redirect("receipts:email_sources")
    else:
        form = EmailImportSourceForm()
    return render(request, "receipts/email_source_form.html", {"form": form, "title": "Добавить почту"})


@login_required
def email_source_update(request, pk):
    source = get_object_or_404(EmailImportSource, pk=pk, user=request.user)
    if request.method == "POST":
        form = EmailImportSourceForm(request.POST, instance=source)
        if form.is_valid():
            form.save()
            messages.success(request, "Источник почты обновлен.")
            return redirect("receipts:email_sources")
    else:
        form = EmailImportSourceForm(instance=source)
    return render(request, "receipts/email_source_form.html", {"form": form, "title": "Редактировать почту"})


@login_required
def email_source_delete(request, pk):
    source = get_object_or_404(EmailImportSource, pk=pk, user=request.user)
    if request.method == "POST":
        source.delete()
        messages.success(request, "Источник почты удален.")
    return redirect("receipts:email_sources")


@login_required
def email_import_run(request, pk):
    source = get_object_or_404(EmailImportSource, pk=pk, user=request.user)
    try:
        count = EmailImportService(source).run()
        messages.success(request, f"Импортировано писем: {count}.")
    except Exception as exc:
        messages.error(request, f"Не удалось импортировать почту: {exc}")
    return redirect("receipts:email_sources")
