from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).select_related("product")
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def mark_all_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
