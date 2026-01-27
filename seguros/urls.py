"""

URL configuration for seguros project.

The `urlpatterns` list routes URLs to views. For more information please see:

    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:

Function views

    1. Add an import:  from my_app import views

    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views

    1. Add an import:  from other_app.views import Home

    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf

    1. Import the include() function: from django.urls import include, path

    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from app.views import CustomLoginView, custom_logout


def health_check(request):
    """Endpoint de health check para Railway y otros servicios de monitoreo."""
    return JsonResponse({"status": "ok", "service": "seguros-utpl"})


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("", include("app.urls")),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", custom_logout, name="logout"),
]

# Serve media files during development (DEBUG mode only)

# This should NOT be used in production - configure your web server to serve media files instead

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
