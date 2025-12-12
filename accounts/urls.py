# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Main page -> Shows Profile (checks if logged in automatically)
    path('', views.profile_view, name='root'),
    
    # Profile link -> Shows Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Login/Signup/Logout
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]