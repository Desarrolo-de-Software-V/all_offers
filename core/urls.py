from django.urls import path
from . import views

urlpatterns = [
    # Páginas públicas
    path('', views.home, name='home'),
    path('offers/', views.offers_list, name='offers_list'),
    path('offers/<int:pk>/', views.offer_detail, name='offer_detail'),
    path('businesses/', views.businesses_list, name='businesses_list'),
    path('business/<int:pk>/', views.business_profile, name='business_profile'),
    
    # Autenticación
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Solicitud de cuenta empresarial
    path('request-business/', views.request_business_account, name='request_business'),
    path('complete-business-profile/', views.complete_business_profile, name='complete_business_profile'),
    
    # Perfil de usuario
    path('profile/', views.user_profile, name='user_profile'),
    path('following/', views.user_following, name='user_following'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    
    # Dashboard de empresas
    path('business-dashboard/', views.business_dashboard, name='business_dashboard'),
    path('business-dashboard/offers/', views.business_my_offers, name='business_my_offers'),
    path('business-dashboard/offers/create/', views.business_create_offer, name='business_create_offer'),
    path('business-dashboard/offers/<int:pk>/edit/', views.business_edit_offer, name='business_edit_offer'),
    path('business-dashboard/offers/<int:pk>/delete/', views.business_delete_offer, name='business_delete_offer'),
    path('business-dashboard/appeal-veto/', views.business_appeal_veto, name='business_appeal_veto'),
    
    # Dashboard de administrador
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/verify-businesses/', views.admin_verify_businesses, name='admin_verify_businesses'),
    path('admin-dashboard/verify-businesses/<int:pk>/approve/', views.admin_approve_business, name='admin_approve_business'),
    path('admin-dashboard/verify-businesses/<int:pk>/reject/', views.admin_reject_business, name='admin_reject_business'),
    path('admin-dashboard/manage-users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin-dashboard/manage-users/<int:pk>/veto/', views.admin_veto_business, name='admin_veto_business'),
    path('admin-dashboard/manage-users/<int:pk>/remove-veto/', views.admin_remove_veto, name='admin_remove_veto'),
    path('admin-dashboard/manage-offers/', views.admin_manage_offers, name='admin_manage_offers'),
    path('admin-dashboard/manage-offers/<int:pk>/delete/', views.admin_delete_offer, name='admin_delete_offer'),
    path('admin-dashboard/statistics/', views.admin_statistics, name='admin_statistics'),
    
    # Reseñas
    path('offers/<int:offer_id>/review/create/', views.create_review, name='create_review'),
    path('reviews/<int:pk>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),
    path('api/reviews/<int:review_id>/like/', views.toggle_review_like, name='toggle_review_like'),
    path('api/reviews/<int:review_id>/dislike/', views.toggle_review_dislike, name='toggle_review_dislike'),
    path('reviews/<int:review_id>/reply/', views.create_review_reply, name='create_review_reply'),
    path('replies/<int:pk>/edit/', views.edit_reply, name='edit_reply'),
    path('replies/<int:pk>/delete/', views.delete_reply, name='delete_reply'),
    path('api/replies/<int:reply_id>/like/', views.toggle_reply_like, name='toggle_reply_like'),
    path('api/replies/<int:reply_id>/dislike/', views.toggle_reply_dislike, name='toggle_reply_dislike'),
    
    # Acciones AJAX
    path('api/offers/<int:offer_id>/like/', views.toggle_like, name='toggle_like'),
    path('api/business/<int:business_id>/follow/', views.toggle_follow_business, name='toggle_follow_business'),
    path('api/category/<int:category_id>/follow/', views.toggle_follow_category, name='toggle_follow_category'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/unread-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('api/search/', views.search_api, name='search_api'),
]