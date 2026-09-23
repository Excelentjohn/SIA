from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('LostFound_list', views.LostFound, name='LostFound_list'),
]