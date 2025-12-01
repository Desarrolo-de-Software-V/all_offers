from math import radians, sin, cos, sqrt, atan2
from django.db.models import Avg, Count, Q
from django.utils import timezone


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcular distancia entre dos puntos usando la fórmula de Haversine
    Retorna la distancia en kilómetros
    """
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return distance


def get_nearby_offers(user_lat, user_lon, max_distance_km=10):
    """
    Obtener ofertas cercanas a una ubicación
    """
    from .models import Offer
    
    active_offers = Offer.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now(),
        business__business_verified=True,
        business__business_vetted=False
    ).select_related('business', 'category')
    
    nearby_offers = []
    for offer in active_offers:
        if offer.business.latitude and offer.business.longitude:
            distance = calculate_distance(
                user_lat, user_lon,
                offer.business.latitude, offer.business.longitude
            )
            if distance <= max_distance_km:
                offer.distance = round(distance, 2)
                nearby_offers.append(offer)
    
    # Ordenar por distancia
    nearby_offers.sort(key=lambda x: x.distance)
    return nearby_offers


def get_popular_offers(limit=10):
    """
    Obtener ofertas más populares basadas en vistas, likes y reseñas
    """
    from .models import Offer
    
    offers = Offer.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now(),
        business__business_verified=True,
        business__business_vetted=False
    ).annotate(
        likes_count=Count('likes'),
        reviews_count=Count('reviews'),
        avg_rating=Avg('reviews__rating')
    ).select_related('business', 'category')
    
    # Calcular puntuación de popularidad
    offers_with_score = []
    for offer in offers:
        score = (
            offer.views * 1 +
            offer.likes_count * 5 +
            offer.reviews_count * 10 +
            (offer.avg_rating or 0) * 20
        )
        # Crear una tupla con el score para ordenar (no asignar a la propiedad)
        offers_with_score.append((score, offer))
    
    # Ordenar por puntuación (mayor a menor)
    offers_with_score.sort(key=lambda x: x[0], reverse=True)
    # Retornar solo los objetos offer, sin el score
    return [offer for score, offer in offers_with_score[:limit]]


def get_expiring_soon_offers(days=3, limit=10):
    """
    Obtener ofertas que están por vencer
    """
    from .models import Offer
    from datetime import timedelta
    
    expiring_date = timezone.now() + timedelta(days=days)
    
    return Offer.objects.filter(
        is_active=True,
        expires_at__lte=expiring_date,
        expires_at__gt=timezone.now(),
        business__business_verified=True,
        business__business_vetted=False
    ).select_related('business', 'category').order_by('expires_at')[:limit]


def search_offers(query, category=None, min_price=None, max_price=None):
    """
    Buscar ofertas con filtros
    """
    from .models import Offer
    
    offers = Offer.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now(),
        business__business_verified=True,
        business__business_vetted=False
    )
    
    if query:
        offers = offers.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(business__business_name__icontains=query)
        )
    
    if category:
        offers = offers.filter(category=category)
    
    if min_price is not None:
        # Filtrar por precio final calculado es más complejo
        # Por ahora filtramos por precio original
        offers = offers.filter(original_price__gte=min_price)
    
    if max_price is not None:
        offers = offers.filter(original_price__lte=max_price)
    
    return offers.select_related('business', 'category').distinct()


def get_dashboard_stats(business):
    """
    Obtener estadísticas para el dashboard de empresa
    """
    from .models import Offer, Review
    from django.db.models import Avg, Sum
    
    total_offers = business.offers.count()
    active_offers = business.offers.filter(
        is_active=True,
        expires_at__gt=timezone.now()
    ).count()
    
    total_views = business.offers.aggregate(Sum('views'))['views__sum'] or 0
    total_likes = sum(offer.likes.count() for offer in business.offers.all())
    
    reviews = Review.objects.filter(offer__business=business)
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    followers_count = business.followers.count()
    
    return {
        'total_offers': total_offers,
        'active_offers': active_offers,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'followers_count': followers_count,
    }


def get_admin_stats():
    """
    Obtener estadísticas para el dashboard del admin
    """
    from .models import User, Offer, BusinessRequest, Payment
    from django.db.models import Sum, Count
    
    total_users = User.objects.filter(role='user').count()
    total_businesses = User.objects.filter(role='business', business_verified=True).count()
    pending_requests = BusinessRequest.objects.filter(status='pending').count()
    vetted_businesses = User.objects.filter(business_vetted=True).count()
    
    total_offers = Offer.objects.count()
    active_offers = Offer.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now()
    ).count()
    
    total_revenue = Payment.objects.filter(status='completed').aggregate(
        Sum('amount')
    )['amount__sum'] or 0
    
    # Ofertas por categoría
    offers_by_category = Offer.objects.values(
        'category__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    return {
        'total_users': total_users,
        'total_businesses': total_businesses,
        'pending_requests': pending_requests,
        'vetted_businesses': vetted_businesses,
        'total_offers': total_offers,
        'active_offers': active_offers,
        'total_revenue': total_revenue,
        'offers_by_category': offers_by_category,
    }