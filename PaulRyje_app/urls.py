from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('catalog/', views.book_catalog, name='book_catalog'),
    path('catalog/add/', views.book_create, name='book_create'),
    path('catalog/<int:pk>/edit/', views.book_update, name='book_update'),
    path('catalog/<int:pk>/delete/', views.book_delete, name='book_delete'),

    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.member_create, name='member_create'),
    path('members/<int:pk>/edit/', views.member_update, name='member_update'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),

    path('borrowing/', views.borrowing_list, name='borrowing_list'),
    path('borrowing/add/', views.borrowing_create, name='borrowing_create'),
    path('borrowing/<int:pk>/return/', views.borrowing_return, name='borrowing_return'),

    path('reports/', views.reports, name='reports'),
    path('settings/', views.library_settings, name='library_settings'),
]
