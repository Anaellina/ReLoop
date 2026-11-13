from django.contrib import admin
from .models import Product, Wishlist, PurchaseRequest, SwapRequest


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'price', 'condition', 'listing_type', 'is_available')
    list_filter = ('category', 'condition', 'listing_type', 'is_available')
    search_fields = ('title', 'description', 'location')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'product', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(SwapRequest)
class SwapRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'requested_product', 'offered_product', 'status')
    list_filter = ('status',)