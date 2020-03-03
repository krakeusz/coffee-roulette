from django.urls import path
from . import views

app_name = 'matcher'
urlpatterns = [
    path('', views.roulette_list_active, name='list_active'),
    path('archive', views.roulette_list_archive, name='list_archive'),
    path('all', views.roulette_list_all, name='list_all'),
    path('roulette/<int:roulette_id>/', views.roulette, name='roulette'),
    path('roulette/<int:roulette_id>/run/', views.run_roulette, name='run'),
    path('roulette/<int:roulette_id>/submit/', views.submit_roulette, name='submit'),
]