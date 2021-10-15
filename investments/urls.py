from django.urls import path
from . import views


urlpatterns = [
    path('', views.index_page, name='index'),
    path('load_graph', views.load_graph, name='load_graph')
]
