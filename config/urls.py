from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.static import serve

from genealogy import views as genealogy_views

urlpatterns = [
    path("admin/export-gedcom/", genealogy_views.export_gedcom_view, name="admin_export_gedcom"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("genealogy.urls")),
    path(
        "media/<path:path>",
        login_required(serve),
        {"document_root": settings.MEDIA_ROOT},
    ),
]
