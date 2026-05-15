from django.urls import path
from . import views

app_name = 'core'

# --- Forum temporarily disabled (no /forum/ routes). To restore:
# 1. Uncomment the two path() lines below.
# 2. Uncomment "core:forum" in core/sitemaps.py (items list).
# 3. Uncomment Forum nav links in templates/core/base.html (search FORUM DISABLED).
# 4. Uncomment the Forum CTA <section> in templates/core/homepage.html (search FORUM DISABLED).

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('', views.homepage, name='homepage'),
    path('homepage/', views.homepage, name='homepage_path'),
    path('about/', views.about, name='about'),
    path('news/', views.news, name='news'),
    path('news/<slug:slug>/', views.news_article, name='news_article'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/<slug:slug>/', views.portfolio_gallery, name='portfolio_gallery'),
    path('shop/', views.shop, name='shop'),
    path('free-models/', views.free_models, name='free_models'),
    path('api/cart/', views.cart_api, name='cart_api'),
    # path('forum/', views.forum, name='forum'),
    # path('forum/<int:topic_id>/', views.forum_topic, name='forum_topic'),
    path('sign-up-login/', views.sign_up_login, name='sign_up_login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/products/add/', views.profile_add_product, name='profile_add_product'),
    path('profile/articles/add/', views.profile_add_article, name='profile_add_article'),
    path('profile/password/', views.profile_password_change, name='profile_password_change'),
    path('profile/site-settings/', views.profile_site_settings, name='profile_site_settings'),
    path('password-reset/', views.CorePasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CorePasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CorePasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CorePasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('copyright/', views.copyright, name='copyright'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/confirmation/', views.order_confirmation, name='order_confirmation'),
]
