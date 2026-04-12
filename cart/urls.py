from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('add/<int:stock_id>/', views.cart_add, name='cart_add'),
    path('detail/', views.cart_detail, name='cart_detail'),
    path('remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
]