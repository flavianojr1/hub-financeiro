"""
Configuração de URLs do projeto hub-financeiro.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.pages.urls')),
    path('dashboard/', include('apps.invoices.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('apps.pages.auth_urls')),  # Custom auth views like signup
]
