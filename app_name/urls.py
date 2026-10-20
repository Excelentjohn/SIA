from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'), path('dashboard/', views.dashboard, name='dashboard_alias'), path('cases/', views.case_list, name='cases'),
    path('login/', views.ArchiveLoginView.as_view(), name='login'), path('logout/', views.ArchiveLogoutView.as_view(), name='logout'), path('register/', views.register, name='register'),
    path('items/add/', views.item_create, name='item_create'), path('items/<int:pk>/edit/', views.item_edit, name='item_edit'), path('items/<str:kind>/', views.item_list, name='item_list'),
    path('save-case/', views.item_create, name='save_case'), path('save-case/<int:pk>/', views.item_edit, name='save_case_update'),
    path('case/<int:pk>/', views.case_detail, name='case_detail'), path('case/<int:pk>/status/<str:target>/', views.transition_case, name='transition_case'), path('delete-case/<int:pk>/', views.delete_case, name='delete_case'),
    path('categories/', views.directory, {'kind': 'categories'}, name='categories'), path('locations/', views.directory, {'kind': 'locations'}, name='locations'),
    path('<str:kind>/<int:pk>/edit/', views.directory_edit, name='directory_edit'), path('<str:kind>/<int:pk>/delete/', views.directory_delete, name='directory_delete'),
    path('reports/', views.reports, name='reports'), path('profile/', views.profile, name='profile'), path('settings/', views.settings_page, name='settings'),
]
