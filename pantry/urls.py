from django.urls import path

from . import views

app_name = "pantry"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("recipes/", views.recipe_ideas, name="recipe_ideas"),
    path("stats/waste/", views.waste_stats, name="waste_stats"),
    path("products/add/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_update, name="product_update"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/used/", views.product_mark_used, name="product_mark_used"),
    path("products/<int:pk>/wasted/", views.product_mark_wasted, name="product_mark_wasted"),
]
