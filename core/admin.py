from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (User, Category, Offer, Review, ReviewReply, BusinessRequest, 
                     VetoAppeal, Notification, Payment)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'business_verified', 'business_vetted', 'date_joined']
    list_filter = ['role', 'business_verified', 'business_vetted', 'is_staff']
    search_fields = ['username', 'email', 'business_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {
            'fields': ('role', 'profile_image', 'phone', 'latitude', 'longitude', 
                      'location_name', 'notifications_enabled')
        }),
        ('Información de empresa', {
            'fields': ('business_name', 'business_description', 'business_verified', 
                      'business_vetted', 'veto_reason')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'color']
    search_fields = ['name']


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'business', 'category', 'original_price', 'final_price', 
                   'discount_type', 'discount_value', 'expires_at', 'is_active', 'views']
    list_filter = ['category', 'discount_type', 'is_active', 'created_at']
    search_fields = ['title', 'business__business_name']
    date_hierarchy = 'created_at'
    
    def final_price(self, obj):
        return f'${obj.final_price:.2f}'
    final_price.short_description = 'Precio Final'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'offer', 'rating', 'likes_count', 'dislikes_count', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'offer__title', 'comment']
    date_hierarchy = 'created_at'
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'
    
    def dislikes_count(self, obj):
        return obj.dislikes.count()
    dislikes_count.short_description = 'Dislikes'


@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ['user', 'review', 'likes_count', 'dislikes_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'review__comment', 'comment']
    date_hierarchy = 'created_at'
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'
    
    def dislikes_count(self, obj):
        return obj.dislikes.count()
    dislikes_count.short_description = 'Dislikes'


@admin.register(BusinessRequest)
class BusinessRequestAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'created_at']
    search_fields = ['business_name', 'user__username']
    date_hierarchy = 'created_at'


@admin.register(VetoAppeal)
class VetoAppealAdmin(admin.ModelAdmin):
    list_display = ['business', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['business__business_name']
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    date_hierarchy = 'created_at'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['business', 'payment_type', 'amount', 'status', 'created_at']
    list_filter = ['payment_type', 'status', 'created_at']
    search_fields = ['business__business_name']
    date_hierarchy = 'created_at'