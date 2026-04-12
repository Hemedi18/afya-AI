import io
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from cart.models import Cart, CartItem
from inventory.models import PharmacyStock
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

@login_required
def order_list(request):
	# Querying the Order model from the cart app where checkout data is saved
	orders = Order.objects.filter(user=request.user).order_by('-created_at')
	return render(request, 'orders/order_list.html', {'orders': orders})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'suborders__pharmacy',
            'suborders__items__stock_item__medicine',
            'suborders__delivery_assignment'  # Only prefetch direct relation to avoid errors
        ),
        pk=pk,
        user=request.user
    )
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def reorder_order(request, pk):
    """Takes items from a past order and adds them to the current active cart."""
    old_order = get_object_or_404(Order, pk=pk, user=request.user)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    for suborder in old_order.suborders.all():
        for item in suborder.items.all():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                stock=item.stock_item,
                defaults={'quantity': item.quantity}
            )
            if not created:
                cart_item.quantity += item.quantity
                cart_item.save()

    messages.success(request, f"Items from Order #{old_order.id} have been added to your cart.")
    return redirect('cart:cart_detail')

@login_required
@transaction.atomic
def cancel_order(request, pk):
    """
    Cancels an order and restores stock levels if none of the sub-orders 
    have been confirmed by pharmacies yet.
    """
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    # Check if any sub-order is already confirmed or further along
    if order.suborders.exclude(status='pending').exists():
        messages.error(request, "This order cannot be cancelled because one or more pharmacies have already started processing it.")
        return redirect('orders:order_detail', pk=pk)
        
    for suborder in order.suborders.all():
        for item in suborder.items.all():
            stock = item.stock_item
            stock.quantity += item.quantity
            stock.save()
        
        suborder.status = 'cancelled'
        suborder.save()
        
    messages.success(request, f"Order #{order.id} has been successfully cancelled and stock has been restored.")
    return redirect('orders:order_list')

@login_required
def generate_order_invoice(request, pk):
    """
    Generates a PDF invoice for a specific order.
    """
    if not REPORTLAB_AVAILABLE:
        messages.error(request, "PDF generation library is not installed. Please contact support.")
        return redirect('orders:order_detail', pk=pk)

    order = get_object_or_404(
        Order.objects.prefetch_related(
            'suborders__pharmacy',
            'suborders__items__stock_item__medicine'
        ),
        pk=pk,
        user=request.user
    )
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"INVOICE - Order #{order.id}")
    
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 70, f"Customer: {order.user.username}")
    p.drawString(50, height - 85, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    p.drawString(50, height - 100, f"Shipping Address: {order.shipping_address}")
    
    y = height - 140
    p.line(50, y + 10, width - 50, y + 10)
    
    for suborder in order.suborders.all():
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, f"Pharmacy: {suborder.pharmacy.name}")
        y -= 20
        
        p.setFont("Helvetica", 10)
        for item in suborder.items.all():
            line = f"{item.stock_item.medicine.generic_name} x {item.quantity}"
            price = f"{item.price_at_time_of_purchase} TZS"
            p.drawString(70, y, line)
            p.drawRightString(width - 70, y, price)
            y -= 15
            
    p.setFont("Helvetica-Bold", 14)
    p.drawRightString(width - 50, y - 30, f"Grand Total: {order.total_amount} TZS")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
