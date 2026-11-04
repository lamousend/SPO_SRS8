from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_index, name='dashboard_index'),
    path('<slug:slug>/', views.dashboard_page, name='dashboard_page'),
    path('<slug:slug>/export.csv', views.dashboard_export, name='dashboard_export'),
]
