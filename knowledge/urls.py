from django.urls import path

from . import views

app_name = "knowledge"

urlpatterns = [
    path("", views.rule_list, name="rule_list"),
    path("add/", views.rule_create, name="rule_create"),
    path("<int:pk>/edit/", views.rule_update, name="rule_update"),
    path("<int:pk>/delete/", views.rule_delete, name="rule_delete"),
]
