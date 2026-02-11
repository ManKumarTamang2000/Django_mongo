from django.urls import path
from .views import recommend_animals

urlpatterns = [
    path('recommend/', recommend_animals, name='recommend_animals'),
]
