from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from decimal import Decimal
from .models import Product, Customer, Order, OrderItem
from .forms import ProductForm, CheckoutForm

class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.request.session.get('cart', {})
        return context

def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart = request.session.get('cart', {})
    qty = cart.get(slug, 0)
    cart[slug] = qty + 1
    request.session['cart'] = cart
    messages.success(request, f'{product.name} added to cart!')
    return redirect('product_detail', slug=slug)

def cart_view(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(slug__in=cart)
    total = Decimal('0')
    cart_items = []
    for product in products:
        qty = cart.get(product.slug, 0)
        subtotal = product.price * Decimal(qty)
        total += subtotal
        cart_items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
    context = {'cart_items': cart_items, 'total': total}
    return render(request, 'store/cart.html', context)

def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    products = Product.objects.filter(slug__in=cart)
    total = Decimal('0')
    cart_items = []
    for product in products:
        qty = cart.get(product.slug, 0)
        subtotal = product.price * Decimal(qty)
        total += subtotal
        cart_items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create customer and order
            customer = Customer.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                address=form.cleaned_data['address']
            )
            order = Order.objects.create(customer=customer, total=total)
            
            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['qty'],
                    price=item['product'].price
                )
            
            # Clear cart
            del request.session['cart']
            
            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('product_list')
    else:
        form = CheckoutForm()
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'store/checkout.html', context)

class AddProductView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/add_product.html'
    success_url = reverse_lazy('product_list')

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, 'Product added successfully!')
        return super().form_valid(form)
