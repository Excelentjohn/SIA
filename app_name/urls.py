from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('save-case/', views.save_case, name='save_case'),
    path('save-case/<int:pk>/', views.save_case, name='save_case_update'),
    path('case/<int:pk>/', views.case_detail, name='case_detail'),
    path('delete-case/<int:pk>/', views.delete_case, name='delete_case'),
    path('LostFound_list', views.LostFound, name='LostFound_list'),
]