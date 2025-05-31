from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Product, Reapprovisionnement, Sortie, Entrepot

@admin.register(Entrepot)
class EntrepotAdmin(admin.ModelAdmin):
    list_display = ['nom', 'adresse']
    search_fields = ['nom']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'stock', 'price', 'entrepots']
    list_filter = ['entrepots']
    search_fields = ['name', 'description']
    readonly_fields = ['stock']  # Stock calculé automatiquement
    
    actions = ['recalculer_stocks']
    
    def recalculer_stocks(self, request, queryset):
        """Action admin pour recalculer les stocks sélectionnés"""
        count = 0
        for product in queryset:
            old_stock = product.stock
            new_stock = product.update_stock()
            if old_stock != new_stock:
                count += 1
        
        if count:
            self.message_user(request, f"{count} stock(s) mis à jour.")
        else:
            self.message_user(request, "Tous les stocks étaient déjà corrects.")
    
    recalculer_stocks.short_description = "Recalculer les stocks sélectionnés"

@admin.register(Sortie)
class SortieAdmin(admin.ModelAdmin):
    list_display = ['produit', 'quantite', 'date_sortie', 'entrepot']
    list_filter = ['date_sortie', 'entrepot']
    search_fields = ['produit__name', 'remarque']
    date_hierarchy = 'date_sortie'
    
    def save_model(self, request, obj, form, change):
        """Validation supplémentaire lors de la sauvegarde en admin"""
        # Vérification du stock disponible avant la sortie
        if not change:  # Seulement pour les nouvelles sorties
            if obj.quantite > obj.produit.stock:
                from django.contrib import messages
                messages.warning(
                    request, 
                    f"Attention : Stock insuffisant pour {obj.produit.name}. "
                    f"Stock disponible: {obj.produit.stock}, demandé: {obj.quantite}"
                )
        super().save_model(request, obj, form, change)

@admin.register(Reapprovisionnement)
class ReapprovisionnementAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantite', 'date_commande', 'date_reception', 'est_recu']
    list_filter = ['date_commande', 'date_reception', 'entrepot']
    search_fields = ['product__name']
    date_hierarchy = 'date_commande'
    
    actions = ['marquer_comme_recu']
    
    def marquer_comme_recu(self, request, queryset):
        """Action pour marquer les réapprovisionnements comme reçus"""
        count = 0
        for reappro in queryset:
            if reappro.marquer_comme_recu():
                count += 1
        
        if count:
            self.message_user(request, f"{count} réapprovisionnement(s) marqué(s) comme reçu(s).")
        else:
            self.message_user(request, "Aucun réapprovisionnement à marquer (déjà reçus).")
    
    marquer_comme_recu.short_description = "Marquer comme reçu"


# Commande de management pour vérifier/corriger les stocks
# À placer dans management/commands/verify_stocks.py

"""
from django.core.management.base import BaseCommand
from votre_app.models import Product

class Command(BaseCommand):
    help = 'Vérifie et corrige les stocks de tous les produits'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corrige automatiquement les stocks incohérents',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Affiche les détails pour chaque produit',
        )
    
    def handle(self, *args, **options):
        products = Product.objects.all()
        incoherent_count = 0
        
        for product in products:
            details = product.get_stock_details()
            
            if not details['coherent']:
                incoherent_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"INCOHÉRENCE - {product.name}: "
                        f"Stock BD={details['stock_actuel']}, "
                        f"Stock calculé={details['stock_calcule']}"
                    )
                )
                
                if options['fix']:
                    old_stock = product.stock
                    product.update_stock()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  → Corrigé: {old_stock} → {product.stock}"
                        )
                    )
            elif options['verbose']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK - {product.name}: Stock={details['stock_actuel']}"
                    )
                )
        
        if incoherent_count == 0:
            self.stdout.write(
                self.style.SUCCESS("Tous les stocks sont cohérents ✓")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"{incoherent_count} produit(s) avec des incohérences"
                )
            )
"""