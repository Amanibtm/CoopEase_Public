from django.urls import path
from . import views


urlpatterns=[
    path('viewspaces/', views.ViewSpaces, name='viewSpaces'),
    path('vieweqp/', views.ViewEquipements, name='viewEqp'),
    path('viewadvusers/', views.ViewAdvancedUsers, name='viewAdvusers'),
]