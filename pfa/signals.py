from django.db.models.signals import post_save, post_delete, pre_save
from .models import DemandePrevision, ParametresStock, Role, Entrepot, Product,UserProfile,Sortie,Reapprovisionnement
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=Sortie)
def update_stock_after_sortie_save(sender, instance, created, **kwargs):
    """
    Met à jour le stock après création ou modification d'une sortie
    """
    # Utilisation d'une transaction pour éviter les problèmes de concurrence
    with transaction.atomic():
        instance.produit.update_stock()

@receiver(post_delete, sender=Sortie)
def update_stock_after_sortie_delete(sender, instance, **kwargs):
    """
    Met à jour le stock après suppression d'une sortie
    """
    with transaction.atomic():
        instance.produit.update_stock()

@receiver(post_save, sender=Reapprovisionnement)
def update_stock_after_reappro_save(sender, instance, created, **kwargs):
    """
    Met à jour le stock après création ou modification d'un réapprovisionnement
    Le stock n'est impacté que si le réapprovisionnement a une date de réception
    """
    # On met à jour le stock seulement si :
    # 1. C'est un nouveau réapprovisionnement avec date de réception OU
    # 2. La date de réception vient d'être ajoutée/modifiée
    should_update = False
    
    if created and instance.date_reception:
        # Nouveau réapprovisionnement déjà reçu
        should_update = True
    elif not created:
        # Réapprovisionnement existant - vérifier si date_reception a changé
        try:
            old_instance = Reapprovisionnement.objects.get(pk=instance.pk)
            if old_instance.date_reception != instance.date_reception:
                should_update = True
        except Reapprovisionnement.DoesNotExist:
            # Cas rare, mais on met à jour par sécurité
            should_update = True
    
    if should_update:
        with transaction.atomic():
            instance.product.update_stock()

@receiver(post_delete, sender=Reapprovisionnement)
def update_stock_after_reappro_delete(sender, instance, **kwargs):
    """
    Met à jour le stock après suppression d'un réapprovisionnement
    """
    if instance.date_reception:  # Seulement si c'était un réapprovisionnement reçu
        with transaction.atomic():
            instance.product.update_stock()