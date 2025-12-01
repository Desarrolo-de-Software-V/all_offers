from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class User(AbstractUser):
    """Usuario personalizado con roles"""
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('business', 'Empresa'),
        ('user', 'Usuario Final'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    
    # Campos específicos para empresas
    business_name = models.CharField(max_length=200, blank=True)
    business_description = models.TextField(blank=True)
    business_verified = models.BooleanField(default=False)
    business_vetted = models.BooleanField(default=False)
    veto_reason = models.TextField(blank=True)
    
    # Seguimiento
    following_businesses = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        related_name='followers',
        blank=True
    )
    following_categories = models.ManyToManyField(
        'Category', 
        related_name='followers',
        blank=True
    )
    
    def __str__(self):
        if self.role == 'business' and self.business_name:
            return f"{self.business_name} ({self.username})"
        return self.username
    
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    @property
    def is_business(self):
        return self.role == 'business'
    
    @property
    def is_regular_user(self):
        return self.role == 'user'
    
    @property
    def can_create_offers(self):
        return self.is_business and self.business_verified and not self.business_vetted


class BusinessRequest(models.Model):
    """Solicitudes de cambio a cuenta empresarial"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_requests')
    business_name = models.CharField(max_length=200)
    business_description = models.TextField()
    phone = models.CharField(max_length=20)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_requests'
    )
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.business_name} - {self.get_status_display()}"


class VetoAppeal(models.Model):
    """Apelaciones de veto"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]
    
    business = models.ForeignKey(User, on_delete=models.CASCADE, related_name='veto_appeals')
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_response = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Apelación de {self.business.business_name}"


class Category(models.Model):
    """Categorías de ofertas"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Clase de icono (ej: fa-utensils)")
    color = models.CharField(max_length=7, default='#8B9A7E', help_text="Color en formato hex")
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Offer(models.Model):
    """Ofertas creadas por empresas"""
    business = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='offers')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='offers/', null=True, blank=True)
    
    # Precios
    original_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio unitario original. Opcional para ofertas tipo 'buy_x_for_price' (aplica a todo el menú)"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Porcentaje'),
            ('fixed', 'Cantidad Fija'),
            ('buy_x_get_y', 'Compra X Lleva Y (ej: 2x1)'),
            ('buy_x_for_price', 'Compra X por Precio (ej: 2x20$)'),
        ],
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Solo para tipos 'percentage' y 'fixed'"
    )
    quantity_x = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad X (ej: para 2x1, X=2). Solo para tipos 'buy_x_get_y' y 'buy_x_for_price'"
    )
    quantity_y = models.PositiveIntegerField(
        default=1,
        null=True,
        blank=True,
        help_text="Cantidad Y (ej: para 2x1, Y=1). Solo para tipo 'buy_x_get_y'"
    )
    bundle_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio del paquete (ej: para 2x20$, precio=20). Solo para tipo 'buy_x_for_price'"
    )
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    # Métricas
    views = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='liked_offers', blank=True)
    
    # Estado
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.business.business_name}"
    
    @property
    def final_price(self):
        if self.discount_type == 'percentage':
            if self.discount_value and self.original_price:
                discount_amount = self.original_price * (self.discount_value / 100)
                return self.original_price - discount_amount
            return self.original_price or Decimal('0')
        elif self.discount_type == 'fixed':
            if self.discount_value and self.original_price:
                return max(self.original_price - self.discount_value, Decimal('0'))
            return self.original_price or Decimal('0')
        elif self.discount_type == 'buy_x_get_y':
            # Para 2x1: precio por unidad = (precio_original * X) / (X + Y)
            # Ejemplo: 2x1 con precio $12 = (12 * 2) / (2 + 1) = 24 / 3 = $8 por unidad
            if self.quantity_x and self.quantity_y and self.original_price:
                total_items = self.quantity_x + self.quantity_y
                total_price = self.original_price * self.quantity_x
                return total_price / total_items
            return self.original_price or Decimal('0')
        elif self.discount_type == 'buy_x_for_price':
            # Para 2x20$: precio por unidad = bundle_price / X
            # Ejemplo: 2x20$ = 20 / 2 = $10 por unidad
            if self.quantity_x and self.bundle_price:
                return self.bundle_price / self.quantity_x
            return self.original_price or Decimal('0')
        return self.original_price or Decimal('0')
    
    @property
    def discount_amount(self):
        """Cantidad ahorrada"""
        if self.discount_type in ['percentage', 'fixed']:
            if self.original_price:
                return self.original_price - self.final_price
            return Decimal('0')
        elif self.discount_type == 'buy_x_get_y':
            # Ahorro = (precio_original * X) - (precio_final * (X + Y))
            if self.quantity_x and self.quantity_y and self.original_price:
                original_total = self.original_price * self.quantity_x
                final_total = self.final_price * (self.quantity_x + self.quantity_y)
                return original_total - final_total
        elif self.discount_type == 'buy_x_for_price':
            # Ahorro = (precio_original * X) - bundle_price
            # Solo calcular si hay precio original (es opcional para este tipo)
            if self.quantity_x and self.bundle_price and self.original_price:
                original_total = self.original_price * self.quantity_x
                return original_total - self.bundle_price
        return Decimal('0')
    
    @property
    def offer_display(self):
        """Texto descriptivo de la oferta"""
        if self.discount_type == 'percentage':
            if self.discount_value:
                return f"-{self.discount_value}%"
            return ""
        elif self.discount_type == 'fixed':
            if self.discount_value:
                return f"-${self.discount_value}"
            return ""
        elif self.discount_type == 'buy_x_get_y':
            if self.quantity_x and self.quantity_y:
                return f"{self.quantity_x}x{self.quantity_y}"
            return ""
        elif self.discount_type == 'buy_x_for_price':
            if self.quantity_x and self.bundle_price:
                return f"{self.quantity_x}x${self.bundle_price}"
            return ""
        return ""
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def popularity_score(self):
        """Puntuación basada en vistas, likes y reseñas"""
        reviews_count = self.reviews.count()
        avg_rating = self.reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        return (self.views * 1) + (self.likes.count() * 5) + (reviews_count * 10) + (avg_rating * 20)


class Review(models.Model):
    """Reseñas de ofertas"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Interacciones
    likes = models.ManyToManyField(
        User, 
        related_name='liked_reviews',
        blank=True,
        symmetrical=False
    )
    dislikes = models.ManyToManyField(
        User,
        related_name='disliked_reviews',
        blank=True,
        symmetrical=False
    )
    helpful_votes = models.ManyToManyField(
        User, 
        related_name='helpful_reviews',
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['offer', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.offer.title} ({self.rating}★)"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    @property
    def dislikes_count(self):
        return self.dislikes.count()
    
    @property
    def net_likes(self):
        """Likes menos dislikes para ordenamiento"""
        return self.likes.count() - self.dislikes.count()
    
    @property
    def replies_count(self):
        return self.replies.count()


class ReviewReply(models.Model):
    """Respuestas a reseñas"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_replies')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Interacciones
    likes = models.ManyToManyField(
        User,
        related_name='liked_replies',
        blank=True,
        symmetrical=False
    )
    dislikes = models.ManyToManyField(
        User,
        related_name='disliked_replies',
        blank=True,
        symmetrical=False
    )
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Review Replies'
    
    def __str__(self):
        return f"Respuesta de {self.user.username} a {self.review.user.username}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    @property
    def dislikes_count(self):
        return self.dislikes.count()
    
    @property
    def net_likes(self):
        """Likes menos dislikes para ordenamiento"""
        return self.likes.count() - self.dislikes.count()


class Notification(models.Model):
    """Sistema de notificaciones"""
    NOTIFICATION_TYPES = [
        ('new_offer', 'Nueva Oferta'),
        ('business_request', 'Solicitud de Empresa'),
        ('request_approved', 'Solicitud Aprobada'),
        ('request_rejected', 'Solicitud Rechazada'),
        ('veto', 'Veto de Cuenta'),
        ('veto_appeal', 'Apelación de Veto'),
        ('new_review', 'Nueva Reseña'),
        ('offer_expiring', 'Oferta por Vencer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Payment(models.Model):
    """Registro de pagos de empresas"""
    PAYMENT_TYPES = [
        ('monthly', 'Mensualidad'),
        ('per_offer', 'Por Oferta'),
        ('featured', 'Destacado'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    business = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.business.business_name} - ${self.amount}"