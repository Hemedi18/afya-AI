from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Cart, CartItem
from orders.models import Order, SubOrder, OrderItem
from django.db.models import F
from inventory.models import PharmacyStock
from prescriptions.models import Prescription
from .forms import CheckoutForm
from decimal import Decimal

@login_required
def cart_add(request, stock_id):
    stock = get_object_or_404(PharmacyStock, id=stock_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    item, item_created = CartItem.objects.get_or_create(cart=cart, stock=stock, defaults={'quantity': 1})
    if not item_created:
        item.quantity += 1
        item.save()
    
    if request.headers.get('HX-Request'):
        # Return the toast fragment as requested by your templates
        return render(request, 'components/_toast_notification.html', {
            'message': f"{stock.medicine.generic_name} added to cart."
        })
    
    messages.success(request, f"Added {stock.medicine.generic_name} to cart.")
    return redirect('inventory:medicine_list')

@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('stock__medicine', 'stock__pharmacy')
    
    total = sum(item.quantity * item.stock.price for item in items)
    requires_prescription = any(item.stock.medicine.requires_prescription for item in items)
    
    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'items': items,
        'total': total,
        'requires_prescription': requires_prescription
    })

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.all()
    
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect('inventory:medicine_list')

    requires_prescription = any(item.stock.medicine.requires_prescription for item in items)
    total_amount = sum(item.quantity * item.stock.price for item in items)

    if request.method == 'POST':
        form = CheckoutForm(request.POST, request.FILES, requires_prescription=requires_prescription)
        if form.is_valid():
            with transaction.atomic():
                # 1. Create Main Order
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total_amount,
                    shipping_address=form.cleaned_data['shipping_address']
                )

                # 2. Handle Prescription
                if request.FILES.get('prescription_file'):
                    Prescription.objects.create(
                        user=request.user,
                        file=request.FILES['prescription_file'],
                        order=order
                    )

                # 3. Create Sub-Orders per Pharmacy
                pharmacies = {}
                for item in items:
                    p_id = item.stock.pharmacy.id
                    if p_id not in pharmacies:
                        pharmacies[p_id] = SubOrder.objects.create(
                            main_order=order,
                            pharmacy=item.stock.pharmacy,
                            sub_total=Decimal('0.00')
                        )
                    
                    # Create OrderItem
                    OrderItem.objects.create(
                        sub_order=pharmacies[p_id],
                        stock_item=item.stock,
                        quantity=item.quantity,
                        price_at_purchase=item.stock.price
                    )
                    
                    pharmacies[p_id].sub_total += (item.quantity * item.stock.price)
                    pharmacies[p_id].save()
                    
                    # Atomic Inventory Reduction with Safety Check
                    stock = PharmacyStock.objects.select_for_update().get(pk=item.stock.pk)
                    if stock.quantity < item.quantity:
                        raise ValueError(f"Insufficient stock for {stock.medicine.generic_name}")
                    
                    stock.quantity = F('quantity') - item.quantity
                    stock.save()

                # 4. Clear Cart
                items.delete()
                # Note: If you have a Delivery model, create it here.
                
                messages.success(request, "Your order has been placed successfully!")
                return redirect('orders:order_list')
    else:
        form = CheckoutForm(requires_prescription=requires_prescription)

    return render(request, 'cart/checkout.html', {
        'form': form,
        'total_amount': total_amount,
        'requires_prescription': requires_prescription
    })

@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('cart:cart_detail')