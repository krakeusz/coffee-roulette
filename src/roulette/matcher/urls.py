from django.urls import path
from . import views

app_name = 'matcher'
urlpatterns = [
    path('', views.current_roulette, name='current'),
    path('roulette/<int:roulette_id>/', views.roulette, name='roulette'),
    path('roulette/<int:roulette_id>/run/', views.run_roulette, name='run'),
    path('roulette/<int:roulette_id>/submit/', views.submit_roulette, name='submit'),
]