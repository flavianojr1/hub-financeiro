from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_invoice, name='upload'),
    path('faturas/', views.invoice_list, name='invoice_list'),
    path('faturas/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('faturas/<int:pk>/update/', views.invoice_update, name='invoice_update'),
    path('categorias/', views.category_manage, name='category_manage'),
    path('cartoes/', views.card_manage, name='card_manage'),
    path('api/chart-data/', views.get_chart_data, name='chart_data'),
    path('api/stats-data/', views.get_stats_data, name='stats_data'),
    path('api/transactions-data/', views.get_transactions_data, name='transactions_data'),
]
