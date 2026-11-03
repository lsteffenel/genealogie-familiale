from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("genealogy.urls")),
    path(
        "media/<path:path>",
        login_required(serve),
        {"document_root": settings.MEDIA_ROOT},
    ),
]
