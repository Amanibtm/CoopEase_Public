from django.urls import path
from . import views

urlpatterns=[
    path('', views.showSchedule, name='ScheduleDisplay'),
    path('taches/', views.enseignantsSchedules, name='taches'),
    path('modules/', views.ViewModules, name='listeModules'),
]