
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from . import smart_swap_views


urlpatterns = [
    # Home
    path('', views.home, name='home'),
    path('my-orders/', views.my_orders, name='my_orders'),

    # Authentication
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='marketplace/login.html'
        ),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),

    # Dashboard and products
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sell/', views.sell_product, name='sell_product'),
    path(
        'product/<int:product_id>/',
        views.product_detail,
        name='product_detail'
    ),

    # Wishlist
    path(
        'wishlist/add/<int:product_id>/',
        views.add_to_wishlist,
        name='add_to_wishlist'
    ),
    path('wishlist/', views.my_wishlist, name='my_wishlist'),
    path(
        'wishlist/remove/<int:product_id>/',
        views.remove_from_wishlist,
        name='remove_from_wishlist'
    ),

    # SmartSwap
    path(
        'smart-swap/',
        smart_swap_views.smart_swap,
        name='smart_swap'
    ),

    # Payment
    path(
        'checkout/<int:product_id>/',
        views.checkout,
        name='checkout'
    ),
    path(
        'payment/success/',
        views.payment_success,
        name='payment_success'
    ),
]
