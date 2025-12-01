# AllOffers - Plataforma de Ofertas

Plataforma web para gestión de ofertas comerciales con geolocalización y sistema de reseñas.

## Características
- 3 tipos de usuarios: Admin, Empresas, Usuarios finales
- Sistema de verificación de comercios
- Geolocalización con Google Maps
- Reseñas y calificaciones
- Sistema de notificaciones
- Seguimiento de comercios y categorías
- Dashboard estadístico para admin

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Crear base de datos:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Crear superusuario:
```bash
python manage.py createsuperuser
```

4. Ejecutar servidor:
```bash
python manage.py runserver
```

5. Acceder a: http://127.0.0.1:8000

## API Key de Google Maps
Edita `alloffers_project/settings.py` y añade tu clave de API de Google Maps:
```python
GOOGLE_MAPS_API_KEY = 'TU_API_KEY_AQUI'
```

## Usuarios de prueba
- Admin: Se crea con `createsuperuser`
- Empresa: Registrarse y solicitar cambio a empresa
- Usuario: Registro normal