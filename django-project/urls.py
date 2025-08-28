# django core libs
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path, include
# 3rd party libs
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin12321/', admin.site.urls), # change default admin path to reduce bruteforce
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redocs/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redocs'),
    path('', include('apps.users.urls', namespace='users')),
    path('app_customers/', include('apps.app_customers.urls', namespace='app_customers')),
    path('app_employee/', include('apps.app_employee.urls', namespace='app_employee')),
    path('app_quotations/', include('apps.app_quotations.urls', namespace='app_quotations')),
    path('app_invoices/', include('apps.app_invoices.urls', namespace='app_invoices')),
]

# Static and Media files handling
if settings.DEBUG:
    # Development: Serve media files via Django
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Production: Media files should be served by web server (nginx, apache)
    # But for testing, you can temporarily add this line:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)