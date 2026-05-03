from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index', views.index, name='index_alias'),
    path('products', views.products, name='products'),
    path('about', views.about, name='about'),
    path('privacy', views.privacy, name='privacy'),
    path('upload_secure', views.upload_secure, name='upload_secure'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap, name='sitemap'),
]
