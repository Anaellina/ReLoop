
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_POST
from django.db import transaction

import razorpay

from .models import Product, Wishlist, Order, Payment
from .forms import ProductForm


# HOME PAGE
def home(request):
    products = Product.objects.filter(
        is_available=True
    ).order_by('-created_at')

    return render(
        request,
        'marketplace/home.html',
        {'products': products}
    )


# USER REGISTRATION
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(request, 'Welcome to ReLoop!')
            return redirect('home')

    else:
        form = UserCreationForm()

    return render(
        request,
        'marketplace/register.html',
        {'form': form}
    )


# USER DASHBOARD
@login_required
def dashboard(request):
    my_products = Product.objects.filter(
        owner=request.user
    ).order_by('-created_at')

    return render(
        request,
        'marketplace/dashboard.html',
        {'my_products': my_products}
    )
# MY ORDERS
@login_required
def my_orders(request):
    orders = Order.objects.filter(
        buyer=request.user
    ).select_related('product', 'seller').order_by('-created_at')

    sales = Order.objects.filter(
        seller=request.user
    ).select_related('product', 'buyer').order_by('-created_at')

    return render(request, 'marketplace/my_orders.html', {
        'orders': orders,
        'sales': sales,
    })


# SELL PRODUCT
@login_required
def sell_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.save()

            messages.success(
                request,
                'Your product has been listed successfully!'
            )

            return redirect('dashboard')

    else:
        form = ProductForm(initial={
            'title': 'Pink Handbag',
            'description': 'Gently used pink handbag in excellent condition.',
            'price': 500,
            'location': 'Assam',
        })

    return render(
        request,
        'marketplace/sell.html',
        {'form': form}
    )


# PRODUCT DETAILS
def product_detail(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    return render(
        request,
        'marketplace/product_detail.html',
        {'product': product}
    )


# ADD TO WISHLIST
@login_required
@require_POST
def add_to_wishlist(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    messages.success(request, 'Product added to your wishlist! ♡')

    return redirect(
        'product_detail',
        product_id=product.id
    )


# VIEW WISHLIST
@login_required
def my_wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    return render(
        request,
        'marketplace/wishlist.html',
        {'wishlist_items': wishlist_items}
    )


# REMOVE FROM WISHLIST
@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(
        user=request.user,
        product_id=product_id
    ).delete()

    messages.success(request, 'Product removed from your wishlist.')

    return redirect('my_wishlist')


# RAZORPAY PAYMENT CLIENT
def get_razorpay_client():
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )


# CHECKOUT PAGE
@login_required
def checkout(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    if product.owner == request.user:
        messages.error(request, 'You cannot buy your own product.')
        return redirect('product_detail', product_id=product.id)

    if product.listing_type not in ['sell', 'both']:
        messages.error(
            request,
            'This product is available for swapping only.'
        )
        return redirect('product_detail', product_id=product.id)

    if product.price <= 0:
        messages.error(request, 'Invalid product price.')
        return redirect('product_detail', product_id=product.id)

    order = None

    try:
        client = get_razorpay_client()

        order = Order.objects.create(
            buyer=request.user,
            seller=product.owner,
            product=product,
            amount=product.price
        )

        gateway_order = client.order.create({
            'amount': int(product.price * 100),
            'currency': 'INR',
            'receipt': f'reloop_{order.id}'
        })

        Payment.objects.create(
            order=order,
            gateway_order_id=gateway_order['id'],
            status='created'
        )

        return render(
            request,
            'marketplace/checkout.html',
            {
                'product': product,
                'order': order,
                'razorpay_order_id': gateway_order['id'],
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'amount': int(product.price * 100),
            }
        )

    except Exception as e:
        print("RAZORPAY CHECKOUT ERROR:", repr(e))

        if order is not None:
            order.delete()

        messages.error(
            request,
            'Unable to start payment. Check the server terminal.'
        )

        return redirect(
            'product_detail',
            product_id=product.id
        )


# PAYMENT SUCCESS AND VERIFICATION
@login_required
@require_POST
def payment_success(request):
    payment_id = request.POST.get('razorpay_payment_id')
    gateway_order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')

    if not payment_id or not gateway_order_id or not signature:
        messages.error(request, 'Payment details are incomplete.')
        return redirect('home')

    payment = get_object_or_404(
        Payment.objects.select_related('order'),
        gateway_order_id=gateway_order_id,
        order__buyer=request.user
    )

    if payment.status == 'successful':
        messages.success(request, 'Your order is already confirmed!')
        return redirect('home')

    try:
        client = get_razorpay_client()

        client.utility.verify_payment_signature({
            'razorpay_order_id': gateway_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })

        with transaction.atomic():
            payment.gateway_payment_id = payment_id
            payment.gateway_signature = signature
            payment.status = 'successful'
            payment.save()

            payment.order.status = 'paid'
            payment.order.save()

            product = payment.order.product
            product.is_available = False
            product.save()

        messages.success(
            request,
            'Payment successful! Your order is confirmed.'
        )

    except Exception as e:
        print("RAZORPAY PAYMENT VERIFICATION ERROR:", repr(e))

        payment.status = 'failed'
        payment.save()

        messages.error(
            request,
            'Payment verification failed. Please contact support.'
        )

    return redirect('home')
