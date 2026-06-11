from django import forms

from .models import EmailImportSource


class ReceiptTextForm(forms.Form):
    text = forms.CharField(label="Текст чека", widget=forms.Textarea(attrs={"rows": 12}))


class ReceiptFileForm(forms.Form):
    file = forms.FileField(label="Файл чека")
    recognized_text = forms.CharField(
        label="Распознанный текст",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="Если OCR не подключен, вставьте текст вручную после сохранения файла.",
    )


class ReceiptManualTextForm(forms.Form):
    text = forms.CharField(label="Распознанный текст", widget=forms.Textarea(attrs={"rows": 10}))


class EmailImportSourceForm(forms.ModelForm):
    class Meta:
        model = EmailImportSource
        fields = ("name", "host", "port", "username", "password", "use_ssl", "sender_filter", "is_active")
        labels = {
            "host": "Host (IMAP-сервер, например: imap.gmail.com, imap.mail.ru, imap.yandex.ru)",
            "sender_filter": "Sender filter (слова или часть адреса отправителя, например: чек, receipt, магазин, @ofd)",
        }
        widgets = {"password": forms.PasswordInput(render_value=True)}
