from django.conf import settings

def google_maps_api_key(request):
    """Context processor para agregar la API key de Google Maps a todos los templates"""
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    }

