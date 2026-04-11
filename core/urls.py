from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('', views.homepage, name='homepage'),
    path('homepage/', views.homepage, name='homepage_path'),
    path('about/', views.about, name='about'),
    path('news/', views.news, name='news'),
    path('news/<slug:slug>/', views.news_article, name='news_article'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('shop/', views.shop, name='shop'),
    path('api/cart/', views.cart_api, name='cart_api'),
    path('forum/', views.forum, name='forum'),
    path('forum/<int:topic_id>/', views.forum_topic, name='forum_topic'),
    path('sign-up-login/', views.sign_up_login, name='sign_up_login'),
    path('copyright/', views.copyright, name='copyright'),
]
