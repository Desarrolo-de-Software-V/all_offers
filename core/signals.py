from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import BusinessRequest, Offer, Review, Notification, User


@receiver(post_save, sender=BusinessRequest)
def notify_admin_new_business_request(sender, instance, created, **kwargs):
    """Notificar al admin cuando hay nueva solicitud de empresa"""
    if created:
        admins = User.objects.filter(role='admin')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                notification_type='business_request',
                title='Nueva solicitud de empresa',
                message=f'{instance.user.username} ha solicitado convertirse en empresa: {instance.business_name}',
                link=f'/admin-dashboard/verify-businesses/'
            )


@receiver(post_save, sender=BusinessRequest)
def notify_user_request_status(sender, instance, created, **kwargs):
    """Notificar al usuario sobre el estado de su solicitud"""
    if not created and instance.status != 'pending':
        if instance.status == 'approved':
            Notification.objects.create(
                user=instance.user,
                notification_type='request_approved',
                title='¡Solicitud aprobada!',
                message=f'Tu solicitud para {instance.business_name} ha sido aprobada. Ya puedes crear ofertas.',
                link='/business-dashboard/'
            )
        elif instance.status == 'rejected':
            Notification.objects.create(
                user=instance.user,
                notification_type='request_rejected',
                title='Solicitud rechazada',
                message=f'Tu solicitud para {instance.business_name} ha sido rechazada. Razón: {instance.rejection_reason}',
                link='/profile/'
            )


@receiver(post_save, sender=Offer)
def notify_followers_new_offer(sender, instance, created, **kwargs):
    """Notificar a seguidores cuando se crea una nueva oferta"""
    if created:
        # Notificar a seguidores del negocio
        followers = instance.business.followers.filter(notifications_enabled=True)
        for follower in followers:
            Notification.objects.create(
                user=follower,
                notification_type='new_offer',
                title=f'Nueva oferta de {instance.business.business_name}',
                message=f'{instance.title} - {instance.discount_value}% de descuento',
                link=f'/offers/{instance.id}/'
            )
        
        # Notificar a seguidores de la categoría
        category_followers = instance.category.followers.filter(notifications_enabled=True)
        for follower in category_followers:
            if follower not in followers:  # Evitar duplicados
                Notification.objects.create(
                    user=follower,
                    notification_type='new_offer',
                    title=f'Nueva oferta en {instance.category.name}',
                    message=f'{instance.title} de {instance.business.business_name}',
                    link=f'/offers/{instance.id}/'
                )


@receiver(post_save, sender=Review)
def notify_business_new_review(sender, instance, created, **kwargs):
    """Notificar a la empresa cuando recibe una nueva reseña"""
    if created:
        Notification.objects.create(
            user=instance.offer.business,
            notification_type='new_review',
            title='Nueva reseña',
            message=f'{instance.user.username} ha dejado una reseña de {instance.rating}★ en {instance.offer.title}',
            link=f'/offers/{instance.offer.id}/'
        )


@receiver(post_save, sender=User)
def notify_admin_new_business_registration(sender, instance, created, **kwargs):
    """Notificar al admin cuando un usuario se registra como negocio"""
    if created and instance.role == 'business' and not instance.business_verified:
        admins = User.objects.filter(role='admin')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                notification_type='business_request',
                title='Nuevo negocio registrado',
                message=f'{instance.username} se ha registrado como negocio y está pendiente de verificación.',
                link=f'/admin-dashboard/manage-users/'
            )


@receiver(pre_save, sender=User)
def notify_business_veto(sender, instance, **kwargs):
    """Notificar a empresa cuando es vetada"""
    if instance.pk:
        old_instance = User.objects.get(pk=instance.pk)
        if not old_instance.business_vetted and instance.business_vetted:
            Notification.objects.create(
                user=instance,
                notification_type='veto',
                title='Cuenta vetada',
                message=f'Tu cuenta ha sido vetada. Razón: {instance.veto_reason}. Puedes apelar esta decisión.',
                link='/business-dashboard/'
            )


@receiver(pre_save, sender=User)
def notify_business_verification(sender, instance, **kwargs):
    """Notificar a empresa cuando es verificada"""
    if instance.pk and instance.role == 'business':
        old_instance = User.objects.get(pk=instance.pk)
        if not old_instance.business_verified and instance.business_verified:
            Notification.objects.create(
                user=instance,
                notification_type='request_approved',
                title='¡Cuenta verificada!',
                message='Tu cuenta empresarial ha sido verificada. Ya puedes crear y gestionar ofertas.',
                link='/business-dashboard/'
            )