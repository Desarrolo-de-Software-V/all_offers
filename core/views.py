from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from .models import (User, Offer, Category, Review, ReviewReply, BusinessRequest, 
                     Notification, VetoAppeal, Payment)
from .forms import (CustomUserCreationForm, CustomAuthenticationForm, 
                    BusinessRequestForm, OfferForm, ReviewForm, ReviewReplyForm,
                    VetoAppealForm, UserProfileForm, BusinessProfileForm, 
                    BusinessInitialProfileForm, CategoryForm)
from .utils import (get_nearby_offers, get_popular_offers, get_expiring_soon_offers,
                    search_offers, get_dashboard_stats, get_admin_stats)


# ==================== VISTAS PÚBLICAS ====================

def home(request):
    """Página principal"""
    # Ofertas populares
    popular_offers = get_popular_offers(limit=8)
    
    # Ofertas por vencer
    expiring_offers = get_expiring_soon_offers(days=3, limit=6)
    
    # Ofertas cercanas (si el usuario tiene ubicación)
    nearby_offers = []
    if request.user.is_authenticated and request.user.latitude and request.user.longitude:
        nearby_offers = get_nearby_offers(
            request.user.latitude, 
            request.user.longitude,
            max_distance_km=10
        )[:6]
    
    # Categorías
    categories = Category.objects.all()
    
    context = {
        'popular_offers': popular_offers,
        'expiring_offers': expiring_offers,
        'nearby_offers': nearby_offers,
        'categories': categories,
    }
    return render(request, 'home.html', context)


def offers_list(request):
    """Lista de ofertas con filtros"""
    offers = Offer.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now(),
        business__business_verified=True,
        business__business_vetted=False
    ).select_related('business', 'category')
    
    # Filtros
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'recent')
    
    if query:
        offers = offers.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(business__business_name__icontains=query)
        )
    
    if category_id:
        offers = offers.filter(category_id=category_id)
    
    # Ordenamiento
    if sort_by == 'popular':
        offers = offers.annotate(
            likes_count=Count('likes')
        ).order_by('-likes_count', '-views')
    elif sort_by == 'expiring':
        offers = offers.order_by('expires_at')
    elif sort_by == 'price_low':
        offers = offers.order_by('original_price')
    elif sort_by == 'price_high':
        offers = offers.order_by('-original_price')
    else:  # recent
        offers = offers.order_by('-created_at')
    
    # Paginación
    paginator = Paginator(offers, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'sort_by': sort_by,
    }
    return render(request, 'offers/list.html', context)


def businesses_list(request):
    """Lista de negocios para que usuarios puedan seguir"""
    businesses = User.objects.filter(
        role='business',
        business_verified=True,
        business_vetted=False
    ).select_related().annotate(
        offers_count=Count('offers', filter=Q(offers__is_active=True, offers__expires_at__gt=timezone.now())),
        followers_count=Count('followers')
    ).order_by('-followers_count', '-date_joined')
    
    # Filtros
    query = request.GET.get('q', '')
    if query:
        businesses = businesses.filter(
            Q(business_name__icontains=query) |
            Q(business_description__icontains=query) |
            Q(location_name__icontains=query)
        )
    
    # Verificar qué negocios sigue el usuario
    following_ids = []
    if request.user.is_authenticated:
        following_ids = list(request.user.following_businesses.values_list('id', flat=True))
    
    # Paginación
    paginator = Paginator(businesses, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'following_ids': following_ids,
    }
    return render(request, 'businesses/list.html', context)


def offer_detail(request, pk):
    """Detalle de una oferta"""
    offer = get_object_or_404(Offer, pk=pk)
    
    # Incrementar vistas
    offer.views += 1
    offer.save(update_fields=['views'])
    
    # Verificar si el usuario ya dio like
    user_liked = False
    if request.user.is_authenticated:
        user_liked = offer.likes.filter(id=request.user.id).exists()
    
    # Reseñas - obtener todas las reseñas con sus relaciones
    reviews_queryset = offer.reviews.select_related('user').prefetch_related('likes', 'dislikes', 'replies')
    
    # Convertir a lista y ordenar por likes netos en Python para evitar conflictos con @property
    reviews_list = list(reviews_queryset)
    # Ordenar por likes netos (likes - dislikes), luego por fecha
    reviews_list.sort(key=lambda r: (r.net_likes, r.created_at), reverse=True)
    
    # Crear un queryset ordenado usando los IDs ordenados
    if reviews_list:
        ordered_ids = [r.id for r in reviews_list]
        from django.db.models import Case, When, IntegerField
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)], output_field=IntegerField())
        reviews = reviews_queryset.filter(id__in=ordered_ids).order_by(preserved)
    else:
        reviews = reviews_queryset.none()
    
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Verificar si el usuario ya dejó reseña y qué reseñas le gustaron/no le gustaron
    user_review = None
    user_liked_reviews = []
    user_disliked_reviews = []
    if request.user.is_authenticated:
        user_review = reviews_queryset.filter(user=request.user).first()
        user_liked_reviews = list(reviews_queryset.filter(likes=request.user).values_list('id', flat=True))
        user_disliked_reviews = list(reviews_queryset.filter(dislikes=request.user).values_list('id', flat=True))
    
    # Ofertas relacionadas
    related_offers = Offer.objects.filter(
        category=offer.category,
        is_active=True,
        expires_at__gt=timezone.now()
    ).exclude(pk=pk).select_related('business')[:4]
    
    # Verificar si el usuario sigue al negocio
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user.following_businesses.filter(id=offer.business.id).exists()
    
    # Obtener respuestas con sus likes/dislikes
    # Usar el queryset original (sin annotate) para evitar problemas
    from .models import ReviewReply
    review_ids = list(reviews.values_list('id', flat=True))
    review_replies = ReviewReply.objects.filter(
        review_id__in=review_ids
    ).select_related('user', 'review').prefetch_related('likes', 'dislikes')
    
    # Verificar qué respuestas le gustaron/no le gustaron al usuario
    user_liked_replies = []
    user_disliked_replies = []
    if request.user.is_authenticated:
        user_liked_replies = list(review_replies.filter(likes=request.user).values_list('id', flat=True))
        user_disliked_replies = list(review_replies.filter(dislikes=request.user).values_list('id', flat=True))
    
    context = {
        'offer': offer,
        'user_liked': user_liked,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'user_review': user_review,
        'user_liked_reviews': user_liked_reviews,
        'user_disliked_reviews': user_disliked_reviews,
        'user_liked_replies': user_liked_replies,
        'user_disliked_replies': user_disliked_replies,
        'related_offers': related_offers,
        'is_following': is_following,
    }
    return render(request, 'offers/detail.html', context)


# ==================== AUTENTICACIÓN ====================

def register(request):
    """Registro de usuario"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Verificar si se registra como negocio
            register_as_business = form.cleaned_data.get('register_as_business', False)
            if register_as_business:
                user.role = 'business'
                # No se verifica automáticamente, debe ser verificado por admin
                user.business_verified = False
            user.save()
            login(request, user)
            
            if register_as_business:
                # Redirigir a completar perfil de negocio (sin mensaje aquí, se mostrará después)
                return redirect('complete_business_profile')
            else:
                messages.success(request, '¡Cuenta creada exitosamente!')
                return redirect('home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})


def user_login(request):
    """Login de usuario"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.username}!')
                
                # Redirigir según el rol
                if user.is_admin:
                    return redirect('admin_dashboard')
                elif user.is_business:
                    return redirect('business_dashboard')
                else:
                    return redirect('home')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


@login_required
def user_logout(request):
    """Logout de usuario"""
    logout(request)
    messages.info(request, 'Sesión cerrada exitosamente.')
    return redirect('home')


# ==================== SOLICITUD DE CUENTA EMPRESARIAL ====================

@login_required
def request_business_account(request):
    """Solicitar cambio a cuenta empresarial"""
    if request.user.is_business or request.user.is_admin:
        messages.warning(request, 'Ya tienes una cuenta empresarial o de administrador.')
        return redirect('home')
    
    # Verificar si ya tiene una solicitud pendiente
    pending_request = BusinessRequest.objects.filter(
        user=request.user,
        status='pending'
    ).first()
    
    if pending_request:
        messages.info(request, 'Ya tienes una solicitud pendiente de revisión.')
        return redirect('user_profile')
    
    if request.method == 'POST':
        form = BusinessRequestForm(request.POST)
        if form.is_valid():
            business_request = form.save(commit=False)
            business_request.user = request.user
            business_request.save()
            messages.success(request, 'Solicitud enviada exitosamente. Te notificaremos cuando sea revisada.')
            return redirect('user_profile')
    else:
        form = BusinessRequestForm()
    
    return render(request, 'auth/request_business.html', {'form': form})


# ==================== PERFIL DE USUARIO ====================

@login_required
def complete_business_profile(request):
    """Completar perfil inicial de negocio después del registro"""
    if not request.user.is_business:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')
    
    # Si ya tiene nombre de negocio, redirigir al dashboard
    if request.user.business_name:
        return redirect('business_dashboard')
    
    if request.method == 'POST':
        form = BusinessInitialProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                '¡Perfil completado! Tu cuenta empresarial está pendiente de verificación. '
                'Mientras tanto, puedes explorar la plataforma. Te notificaremos cuando sea verificada.'
            )
            return redirect('business_dashboard')
    else:
        form = BusinessInitialProfileForm(instance=request.user)
    
    return render(request, 'auth/complete_business_profile.html', {'form': form})


@login_required
def user_profile(request):
    """Perfil del usuario"""
    if request.method == 'POST':
        if request.user.is_business:
            form = BusinessProfileForm(request.POST, request.FILES, instance=request.user)
        else:
            form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('user_profile')
    else:
        if request.user.is_business:
            form = BusinessProfileForm(instance=request.user)
        else:
            form = UserProfileForm(instance=request.user)
    
    # Obtener solicitud de negocio pendiente si existe
    pending_request = None
    if not request.user.is_business:
        pending_request = BusinessRequest.objects.filter(
            user=request.user,
            status='pending'
        ).first()
    
    context = {
        'form': form,
        'pending_request': pending_request,
    }
    return render(request, 'user/profile.html', context)


@login_required
def user_following(request):
    """Empresas y categorías que sigue el usuario"""
    following_businesses = request.user.following_businesses.filter(
        business_verified=True,
        business_vetted=False
    )
    following_categories = request.user.following_categories.all()
    
    context = {
        'following_businesses': following_businesses,
        'following_categories': following_categories,
    }
    return render(request, 'user/following.html', context)


@login_required
def user_notifications(request):
    """Notificaciones del usuario"""
    notifications = request.user.notifications.all()[:50]
    
    # Marcar como leídas
    request.user.notifications.filter(is_read=False).update(is_read=True)
    
    return render(request, 'user/notifications.html', {'notifications': notifications})


# ==================== DASHBOARD DE EMPRESAS ====================

@login_required
def business_dashboard(request):
    """Dashboard principal de empresas"""
    if not request.user.is_business:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')
    
    # Si no está verificado, mostrar mensaje pero permitir acceso
    is_verified = request.user.business_verified
    
    stats = get_dashboard_stats(request.user) if is_verified else {}
    recent_offers = request.user.offers.all().order_by('-created_at')[:5] if is_verified else []
    recent_reviews = Review.objects.filter(offer__business=request.user).order_by('-created_at')[:5] if is_verified else []
    
    context = {
        'stats': stats,
        'recent_offers': recent_offers,
        'recent_reviews': recent_reviews,
        'is_verified': is_verified,
    }
    return render(request, 'business_dashboard/dashboard.html', context)


@login_required
def business_my_offers(request):
    """Mis ofertas (empresa)"""
    if not request.user.is_business:
        return redirect('home')
    
    offers = request.user.offers.all().order_by('-created_at')
    
    # Filtros
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        offers = offers.filter(is_active=True, expires_at__gt=timezone.now())
    elif status_filter == 'expired':
        offers = offers.filter(expires_at__lte=timezone.now())
    elif status_filter == 'inactive':
        offers = offers.filter(is_active=False)
    
    paginator = Paginator(offers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'business_dashboard/my_offers.html', context)


@login_required
def business_create_offer(request):
    """Crear nueva oferta"""
    if not request.user.can_create_offers:
        if request.user.business_vetted:
            messages.error(request, 'Tu cuenta está vetada. No puedes crear ofertas.')
            return redirect('business_dashboard')
        elif not request.user.business_verified:
            messages.error(request, 'Tu cuenta no está verificada aún.')
            return redirect('business_dashboard')
        return redirect('home')
    
    if request.method == 'POST':
        form = OfferForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                offer = form.save(commit=False)
                offer.business = request.user
                offer.save()
                messages.success(request, 'Oferta creada exitosamente.')
                return redirect('business_my_offers')
            except Exception as e:
                messages.error(request, f'Error al guardar la oferta: {str(e)}')
        else:
            # Si el formulario no es válido, mostrar errores
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
            # Debug: imprimir errores en consola del servidor
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Form errors: {form.errors}')
            logger.error(f'Form data: {request.POST}')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = OfferForm()
    
    return render(request, 'business_dashboard/create_offer.html', {'form': form})


@login_required
def business_edit_offer(request, pk):
    """Editar oferta"""
    offer = get_object_or_404(Offer, pk=pk)
    
    if offer.business != request.user:
        return HttpResponseForbidden('No tienes permiso para editar esta oferta.')
    
    if request.user.business_vetted:
        messages.error(request, 'Tu cuenta está vetada. No puedes editar ofertas.')
        return redirect('business_my_offers')
    
    if request.method == 'POST':
        form = OfferForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta actualizada exitosamente.')
            return redirect('business_my_offers')
    else:
        form = OfferForm(instance=offer)
    
    return render(request, 'business_dashboard/edit_offer.html', {'form': form, 'offer': offer})


@login_required
def business_delete_offer(request, pk):
    """Eliminar oferta"""
    offer = get_object_or_404(Offer, pk=pk)
    
    if offer.business != request.user:
        return HttpResponseForbidden('No tienes permiso para eliminar esta oferta.')
    
    if request.user.business_vetted:
        messages.error(request, 'Tu cuenta está vetada. No puedes eliminar ofertas.')
        return redirect('business_my_offers')
    
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Oferta eliminada exitosamente.')
        return redirect('business_my_offers')
    
    return render(request, 'business_dashboard/confirm_delete.html', {'offer': offer})


@login_required
def business_appeal_veto(request):
    """Apelar veto"""
    if not request.user.business_vetted:
        messages.info(request, 'Tu cuenta no está vetada.')
        return redirect('business_dashboard')
    
    # Verificar si ya tiene una apelación pendiente
    pending_appeal = VetoAppeal.objects.filter(
        business=request.user,
        status='pending'
    ).first()
    
    if pending_appeal:
        messages.info(request, 'Ya tienes una apelación pendiente.')
        return redirect('business_dashboard')
    
    if request.method == 'POST':
        form = VetoAppealForm(request.POST)
        if form.is_valid():
            appeal = form.save(commit=False)
            appeal.business = request.user
            appeal.save()
            messages.success(request, 'Apelación enviada. Será revisada pronto.')
            return redirect('business_dashboard')
    else:
        form = VetoAppealForm()
    
    return render(request, 'business_dashboard/appeal_veto.html', {'form': form})


# ==================== DASHBOARD DE ADMINISTRADOR ====================

@login_required
def admin_dashboard(request):
    """Dashboard principal del administrador"""
    if not request.user.is_admin:
        messages.error(request, 'No tienes permisos de administrador.')
        return redirect('home')
    
    stats = get_admin_stats()
    
    # Actividad reciente
    recent_requests = BusinessRequest.objects.filter(status='pending').order_by('-created_at')[:5]
    recent_offers = Offer.objects.all().order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_requests': recent_requests,
        'recent_offers': recent_offers,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
def admin_verify_businesses(request):
    """Verificar solicitudes de empresas"""
    if not request.user.is_admin:
        return redirect('home')
    
    requests_list = BusinessRequest.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status', 'pending')
    if status_filter != 'all':
        requests_list = requests_list.filter(status=status_filter)
    
    paginator = Paginator(requests_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'admin_dashboard/verify_businesses.html', context)


@login_required
def admin_approve_business(request, pk):
    """Aprobar solicitud de empresa"""
    if not request.user.is_admin:
        return HttpResponseForbidden()
    
    business_request = get_object_or_404(BusinessRequest, pk=pk)
    
    if business_request.status != 'pending':
        messages.warning(request, 'Esta solicitud ya fue procesada.')
        return redirect('admin_verify_businesses')
    
    # Actualizar usuario
    user = business_request.user
    user.role = 'business'
    user.business_name = business_request.business_name
    user.business_description = business_request.business_description
    user.phone = business_request.phone
    user.latitude = business_request.latitude
    user.longitude = business_request.longitude
    user.location_name = business_request.location_name
    user.business_verified = True
    user.save()
    
    # Actualizar solicitud
    business_request.status = 'approved'
    business_request.reviewed_at = timezone.now()
    business_request.reviewed_by = request.user
    business_request.save()
    
    messages.success(request, f'Solicitud de {business_request.business_name} aprobada.')
    return redirect('admin_verify_businesses')


@login_required
def admin_reject_business(request, pk):
    """Rechazar solicitud de empresa"""
    if not request.user.is_admin:
        return HttpResponseForbidden()
    
    business_request = get_object_or_404(BusinessRequest, pk=pk)
    
    if business_request.status != 'pending':
        messages.warning(request, 'Esta solicitud ya fue procesada.')
        return redirect('admin_verify_businesses')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        business_request.status = 'rejected'
        business_request.rejection_reason = reason
        business_request.reviewed_at = timezone.now()
        business_request.reviewed_by = request.user
        business_request.save()
        
        messages.success(request, 'Solicitud rechazada.')
        return redirect('admin_verify_businesses')
    
    return render(request, 'admin_dashboard/reject_business.html', {'business_request': business_request})


@login_required
def admin_manage_users(request):
    """Gestionar usuarios"""
    if not request.user.is_admin:
        return redirect('home')
    
    users = User.objects.all().order_by('-date_joined')
    
    role_filter = request.GET.get('role', 'all')
    if role_filter != 'all':
        users = users.filter(role=role_filter)
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
    }
    return render(request, 'admin_dashboard/manage_users.html', context)


@login_required
def admin_veto_business(request, pk):
    """Vetar una empresa"""
    if not request.user.is_admin:
        return HttpResponseForbidden()
    
    business = get_object_or_404(User, pk=pk, role='business')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        business.business_vetted = True
        business.veto_reason = reason
        business.save()
        
        messages.success(request, f'{business.business_name} ha sido vetado.')
        return redirect('admin_manage_users')
    
    return render(request, 'admin_dashboard/veto_business.html', {'business': business})


@login_required
def admin_remove_veto(request, pk):
    """Quitar veto a una empresa"""
    if not request.user.is_admin:
        return HttpResponseForbidden()
    
    business = get_object_or_404(User, pk=pk, role='business')
    business.business_vetted = False
    business.veto_reason = ''
    business.save()
    
    messages.success(request, f'Veto removido de {business.business_name}.')
    return redirect('admin_manage_users')


@login_required
def admin_manage_offers(request):
    """Gestionar todas las ofertas"""
    if not request.user.is_admin:
        return redirect('home')
    
    offers = Offer.objects.all().select_related('business', 'category').order_by('-created_at')
    
    paginator = Paginator(offers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_dashboard/manage_offers.html', {'page_obj': page_obj})


@login_required
def admin_delete_offer(request, pk):
    """Eliminar oferta (admin)"""
    if not request.user.is_admin:
        return HttpResponseForbidden()
    
    offer = get_object_or_404(Offer, pk=pk)
    offer.delete()
    messages.success(request, 'Oferta eliminada.')
    return redirect('admin_manage_offers')


@login_required
def admin_statistics(request):
    """Estadísticas detalladas"""
    if not request.user.is_admin:
        return redirect('home')
    
    stats = get_admin_stats()
    
    # Datos adicionales para gráficas
    from django.db.models.functions import TruncDate
    
    # Ofertas por día (últimos 30 días)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    offers_by_day = Offer.objects.filter(
        created_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Top empresas por número de ofertas
    top_businesses = User.objects.filter(
        role='business'
    ).annotate(
        offers_count=Count('offers')
    ).order_by('-offers_count')[:10]
    
    context = {
        'stats': stats,
        'offers_by_day': list(offers_by_day),
        'top_businesses': top_businesses,
    }
    return render(request, 'admin_dashboard/statistics.html', context)


# ==================== RESEÑAS ====================

@login_required
def create_review(request, offer_id):
    """Crear reseña"""
    offer = get_object_or_404(Offer, pk=offer_id)
    
    # Verificar que no sea el dueño de la oferta
    if request.user == offer.business:
        return JsonResponse({'error': 'No puedes reseñar tu propia oferta'}, status=400)
    
    # Verificar si ya dejó reseña
    existing_review = Review.objects.filter(offer=offer, user=request.user).first()
    if existing_review:
        return JsonResponse({'error': 'Ya dejaste una reseña para esta oferta'}, status=400)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.offer = offer
            review.user = request.user
            review.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            messages.success(request, 'Reseña publicada exitosamente.')
            return redirect('offer_detail', pk=offer_id)
    
    return redirect('offer_detail', pk=offer_id)


@login_required
def edit_review(request, pk):
    """Editar reseña"""
    review = get_object_or_404(Review, pk=pk)
    
    if review.user != request.user:
        messages.error(request, 'No tienes permisos para editar esta reseña.')
        return redirect('offer_detail', pk=review.offer.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reseña actualizada exitosamente.')
            return redirect('offer_detail', pk=review.offer.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'reviews/edit.html', {'form': form, 'review': review})


@login_required
def delete_review(request, pk):
    """Eliminar reseña"""
    review = get_object_or_404(Review, pk=pk)
    
    if review.user != request.user:
        return HttpResponseForbidden()
    
    offer_id = review.offer.id
    review.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Reseña eliminada.')
    return redirect('offer_detail', pk=offer_id)


@login_required
def toggle_review_like(request, review_id):
    """Dar/quitar like a una reseña"""
    review = get_object_or_404(Review, pk=review_id)
    
    if request.user in review.likes.all():
        review.likes.remove(request.user)
        liked = False
    else:
        review.likes.add(request.user)
        # Si tenía dislike, quitarlo
        if request.user in review.dislikes.all():
            review.dislikes.remove(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': review.likes.count(),
        'dislikes_count': review.dislikes.count(),
        'net_likes': review.net_likes
    })


@login_required
def toggle_review_dislike(request, review_id):
    """Dar/quitar dislike a una reseña"""
    review = get_object_or_404(Review, pk=review_id)
    
    if request.user in review.dislikes.all():
        review.dislikes.remove(request.user)
        disliked = False
    else:
        review.dislikes.add(request.user)
        # Si tenía like, quitarlo
        if request.user in review.likes.all():
            review.likes.remove(request.user)
        disliked = True
    
    return JsonResponse({
        'disliked': disliked,
        'likes_count': review.likes.count(),
        'dislikes_count': review.dislikes.count(),
        'net_likes': review.net_likes
    })


@login_required
def create_review_reply(request, review_id):
    """Crear respuesta a una reseña"""
    review = get_object_or_404(Review, pk=review_id)
    
    if request.method == 'POST':
        form = ReviewReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.review = review
            reply.user = request.user
            reply.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'reply_id': reply.id,
                    'message': 'Respuesta publicada exitosamente.'
                })
            
            messages.success(request, 'Respuesta publicada exitosamente.')
            return redirect('offer_detail', pk=review.offer.id)
    
    return redirect('offer_detail', pk=review.offer.id)


@login_required
def toggle_reply_like(request, reply_id):
    """Dar/quitar like a una respuesta"""
    reply = get_object_or_404(ReviewReply, pk=reply_id)
    
    if request.user in reply.likes.all():
        reply.likes.remove(request.user)
        liked = False
    else:
        reply.likes.add(request.user)
        if request.user in reply.dislikes.all():
            reply.dislikes.remove(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': reply.likes.count(),
        'dislikes_count': reply.dislikes.count()
    })


@login_required
def toggle_reply_dislike(request, reply_id):
    """Dar/quitar dislike a una respuesta"""
    reply = get_object_or_404(ReviewReply, pk=reply_id)
    
    if request.user in reply.dislikes.all():
        reply.dislikes.remove(request.user)
        disliked = False
    else:
        reply.dislikes.add(request.user)
        if request.user in reply.likes.all():
            reply.likes.remove(request.user)
        disliked = True
    
    return JsonResponse({
        'disliked': disliked,
        'likes_count': reply.likes.count(),
        'dislikes_count': reply.dislikes.count()
    })


@login_required
def edit_reply(request, pk):
    """Editar respuesta a una reseña"""
    reply = get_object_or_404(ReviewReply, pk=pk)
    
    if reply.user != request.user:
        messages.error(request, 'No tienes permisos para editar esta respuesta.')
        return redirect('offer_detail', pk=reply.review.offer.id)
    
    if request.method == 'POST':
        form = ReviewReplyForm(request.POST, instance=reply)
        if form.is_valid():
            form.save()
            messages.success(request, 'Respuesta actualizada exitosamente.')
            return redirect('offer_detail', pk=reply.review.offer.id)
    else:
        form = ReviewReplyForm(instance=reply)
    
    return render(request, 'replies/edit.html', {'form': form, 'reply': reply})


@login_required
def delete_reply(request, pk):
    """Eliminar respuesta a una reseña"""
    reply = get_object_or_404(ReviewReply, pk=pk)
    
    if reply.user != request.user:
        messages.error(request, 'No tienes permisos para eliminar esta respuesta.')
        return redirect('offer_detail', pk=reply.review.offer.id)
    
    offer_id = reply.review.offer.id
    reply.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Respuesta eliminada.')
    return redirect('offer_detail', pk=offer_id)


# ==================== ACCIONES AJAX ====================

@login_required
def toggle_like(request, offer_id):
    """Dar/quitar like a una oferta"""
    if request.method == 'POST':
        offer = get_object_or_404(Offer, pk=offer_id)
        
        if request.user in offer.likes.all():
            offer.likes.remove(request.user)
            liked = False
        else:
            offer.likes.add(request.user)
            liked = True
        
        return JsonResponse({
            'liked': liked,
            'likes_count': offer.likes.count()
        })
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def toggle_follow_business(request, business_id):
    """Seguir/dejar de seguir una empresa"""
    if request.method == 'POST':
        business = get_object_or_404(User, pk=business_id, role='business')
        
        if business in request.user.following_businesses.all():
            request.user.following_businesses.remove(business)
            following = False
        else:
            request.user.following_businesses.add(business)
            following = True
        
        return JsonResponse({
            'following': following,
            'followers_count': business.followers.count()
        })
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def toggle_follow_category(request, category_id):
    """Seguir/dejar de seguir una categoría"""
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=category_id)
        
        if category in request.user.following_categories.all():
            request.user.following_categories.remove(category)
            following = False
        else:
            request.user.following_categories.add(category)
            following = True
        
        return JsonResponse({
            'following': following,
            'followers_count': category.followers.count()
        })
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def mark_notification_read(request, notification_id):
    """Marcar notificación como leída"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def get_unread_notifications_count(request):
    """Obtener cantidad de notificaciones no leídas"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


def search_api(request):
    """API de búsqueda (para autocompletado)"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Buscar ofertas
    offers = Offer.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        is_active=True,
        expires_at__gt=timezone.now()
    )[:5]
    
    # Buscar empresas
    businesses = User.objects.filter(
        business_name__icontains=query,
        role='business',
        business_verified=True,
        business_vetted=False
    )[:5]
    
    results = []
    
    for offer in offers:
        results.append({
            'type': 'offer',
            'id': offer.id,
            'title': offer.title,
            'business': offer.business.business_name,
            'url': f'/offers/{offer.id}/'
        })
    
    for business in businesses:
        results.append({
            'type': 'business',
            'id': business.id,
            'title': business.business_name,
            'description': business.business_description[:100],
            'url': f'/business/{business.id}/'
        })
    
    return JsonResponse({'results': results})


def business_profile(request, pk):
    """Perfil público de empresa"""
    business = get_object_or_404(User, pk=pk, role='business')
    
    offers = business.offers.filter(
        is_active=True,
        expires_at__gt=timezone.now()
    ).order_by('-created_at')
    
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user.following_businesses.filter(id=business.id).exists()
    
    stats = get_dashboard_stats(business)
    
    context = {
        'business': business,
        'offers': offers,
        'is_following': is_following,
        'stats': stats,
    }
    return render(request, 'business_dashboard/profile.html', context)