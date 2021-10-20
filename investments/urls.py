from django.urls import path
from . import views


urlpatterns = [
    path('', views.index_page, name='index'),
    path('<int:portfolio_pk>', views.portfolio_page, name='portfolio')
]
