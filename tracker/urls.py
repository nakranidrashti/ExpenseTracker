from django.urls import path
from . import views

urlpatterns = [
    
    path('dashboard/', views.dashboard, name='dashboard'),

    path('category/add/', views.add_category, name='add_category'),
    path('budget/add/', views.add_budget, name='add_budget'),
    path('expense/add/', views.add_expense, name='add_expense'),
    path('income/add/', views.add_income, name='add_income'),

    path('category', views.view_category, name='view_category'),
    path('budget', views.view_budget, name='view_budget'),
    path('income', views.view_income, name='view_income'),
    path('expense', views.view_expense, name='view_expense'),

    path('category/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('budget/edit/<int:pk>/', views.edit_budget, name='edit_budget'),
    path('income/edit/<int:pk>/', views.edit_income, name='edit_income'),
    path('expense/edit/<int:pk>/', views.edit_expense, name='edit_expense'),

    path('category/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('budget/delete/<int:pk>/', views.delete_budget, name='delete_budget'),
    path('income/delete/<int:pk>/', views.delete_income, name='delete_income'),
    path('expense/delete/<int:pk>/', views.delete_expense, name='delete_expense'),

    path("predict-category/", views.predict_category, name="predict_category"),
    
    


    #path('image/', views.image_view, name='image'),
] 
