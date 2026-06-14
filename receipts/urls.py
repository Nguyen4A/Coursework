from django.urls import path

from . import views

app_name = "receipts"

urlpatterns = [
    path("text/", views.import_text, name="import_text"),
    path("file/", views.import_file, name="import_file"),
    path("<int:pk>/", views.detail, name="detail"),
    path("items/<int:pk>/review/", views.review_item, name="item_review"),
    path("email/", views.email_sources, name="email_sources"),
    path("email/add/", views.email_source_create, name="email_source_create"),
    # Existing email sources can be opened again to review and update settings.
    path("email/<int:pk>/edit/", views.email_source_update, name="email_source_update"),
    path("email/<int:pk>/delete/", views.email_source_delete, name="email_source_delete"),
    path("email/<int:pk>/run/", views.email_import_run, name="email_import_run"),
]
