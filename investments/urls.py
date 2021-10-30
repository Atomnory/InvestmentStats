from django.urls import path
from . import views


urlpatterns = [
    path('', views.index_page, name='index'),
    path('<int:portfolio_pk>', views.portfolio_page, name='portfolio'),
    path('delete-portfolio/<int:portfolio_pk>', views.delete_portfolio_page, name='delete_portfolio'),
    path('superuser-dashboard', views.superuser_dashboard, name='superuser_dashboard')
]
