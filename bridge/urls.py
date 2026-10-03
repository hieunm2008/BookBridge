from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/new/', views.inventory_form, name='inventory_new'),
    path('inventory/<int:pk>/edit/', views.inventory_form, name='inventory_edit'),
    path('requests/', views.need_list, name='need_list'),
    path('requests/new/', views.need_form, name='need_new'),
    path('requests/<int:pk>/edit/', views.need_form, name='need_edit'),
    path('requests/<int:pk>/cancel/', views.need_cancel, name='need_cancel'),
    path('coordination/', views.coordination, name='coordination'),
    path('coordination/<int:pk>/', views.proposal_detail, name='proposal_detail'),
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
]
