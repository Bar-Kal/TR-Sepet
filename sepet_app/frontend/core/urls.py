from django.urls import path
from django.views.generic.base import RedirectView
from django.templatetags.static import static
from . import views

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=static('img/page/favicon.ico'), permanent=True)),
    path('', views.index, name='index'),
    path('index', views.index, name='index_alias'),
    path('products', views.products, name='products'),
    path('about', views.about, name='about'),
    path('privacy', views.privacy, name='privacy'),
    path('api/products', views.api_products, name='api_products'),
    path('api/shops', views.api_shops, name='api_shops'),
    path('upload_secure', views.upload_secure, name='upload_secure'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap, name='sitemap'),
]
