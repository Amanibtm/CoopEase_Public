from django.urls import path  # Import path
from . import views

urlpatterns = [
    path('', views.Login, name='login'),
    path('Logout/', views.Logout, name='Logout'),
    path('acceuil-Enseingant/', views.homepage_advuser, name='homepageAdvuser'),
    path('acceuil-Etudiant/', views.homepage_basicuser, name='homepageBasicuser'),
    path('choisirGroup/', views.book_group, name='bookGroup'),
    path('resSalle/', views.book_space, name='bookSpace'),
    path('resOccSalle/', views.book_occasionaly_available_space, name='bookAbsentSpace'),
    path('slctIndisponibilite/', views.select_busy_time, name='SelectBusyTime'),
    path('absence/', views.annonce_absence, name='announceAbsence'),
    path('historiqueReservations/', views.OperationsHistory, name='operationsHistory'),
    path('affichage/', views.tableauAffichage, name='tabAffichage'),
    path('confirmeRes/', views.approve_reservations, name='approveResr'),
    path('confirmeIndipo/', views.confirm_busy_times, name='approveIndispo'),
    path('supp_inspo/<int:entry_id>/', views.delete_busy_entry, name='delete_busy_entry'),
    path('supp_absence/<int:entry_id>/', views.delete_absence, name='delete_absence'),
    path('contact-superuser/', views.contact_superuser, name='contact_superuser'),
    path('profile/', views.profile, name='profile'),
]
