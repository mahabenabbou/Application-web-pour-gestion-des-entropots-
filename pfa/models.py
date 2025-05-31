# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from datetime import timedelta
import math
import numpy as np

class Role(models.Model):
    ADMIN = 'admin'
    DIRECTEUR = 'directeur'
    GESTIONNAIRE = 'gestionnaire'

    ROLE_CHOICES = [
        (ADMIN, 'Administrateur'),
        (DIRECTEUR, 'Directeur'),
        (GESTIONNAIRE, 'Gestionnaire'),
    ]

    name = models.CharField(max_length=20, choices=ROLE_CHOICES, default=GESTIONNAIRE)

    def __str__(self):
        return self.get_name_display()

class Entrepot(models.Model):
    nom = models.CharField(max_length=100)
    ville = models.CharField(max_length=255, null=True)
    adresse = models.CharField(max_length=255, null=True)
    description = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    surface = models.IntegerField(null=True)
    
    # Ajoutez ces nouveaux champs pour le calcul des coûts
    cout_fixe_annuel = models.FloatField(
        default=500.0,
        verbose_name="Coût fixe annuel de l'entrepôt"
    )
    cout_variable_unitaire = models.FloatField(
        default=10.0,
        verbose_name="Coût variable par unité stockée"
    )
    
    @property
    def cout_entreposage(self):
        """Calcule le coût total d'entreposage par unité stockée"""
        # Import local pour éviter les imports circulaires
        from .models import Product
        
        # Récupération explicite des produits de cet entrepôt
        produits = Product.objects.filter(entrepots=self)
        total_products = sum(product.stock for product in produits)
        
        if total_products == 0:
            return 0

        cout_total = self.cout_fixe_annuel + (self.cout_variable_unitaire * total_products)
        return cout_total / total_products
    

    def test_cout_entreposage(self):
        """Méthode de test pour voir ce qui se passe"""
        from .models import Product
        
        print(f"\n=== TEST POUR ENTREPOT: {self.nom} ===")
        
        # Vérifier les coûts configurés
        print(f"Coût fixe annuel: {self.cout_fixe_annuel}")
        print(f"Coût variable unitaire: {self.cout_variable_unitaire}")
        
        # Récupérer les produits
        produits = Product.objects.filter(entrepots=self)
        print(f"Nombre de produits dans cet entrepôt: {produits.count()}")
        
        # Afficher chaque produit et son stock
        total_stock = 0
        for product in produits:
            print(f"  - {product.name}: stock = {product.stock}")
            total_stock += product.stock
        
        print(f"TOTAL STOCK: {total_stock}")
        
        if total_stock == 0:
            print("RESULTAT: 0 (pas de stock)")
            return 0
        
        # Calcul
        cout_total = self.cout_fixe_annuel + (self.cout_variable_unitaire * total_stock)
        cout_par_unite = cout_total / total_stock
        
        print(f"Coût total: {cout_total}")
        print(f"Coût par unité: {cout_par_unite}")
        print("=" * 40)
        
        return cout_par_unite
    
    @property
    def cout_entreposage(self):
        """Calcule le coût total d'entreposage par unité stockée"""
        # Import ici pour éviter les problèmes d'import circulaire
        from .models import Product
        
        # Récupérer tous les produits de cet entrepôt
        produits = Product.objects.filter(entrepots=self)
        
        # Calculer le total du stock
        total_products = 0
        for product in produits:
            total_products += product.stock
        
        # Si pas de stock, retourner 0
        if total_products == 0:
            return 0

        # Calculer le coût total et le coût par unité
        cout_total = self.cout_fixe_annuel + (self.cout_variable_unitaire * total_products)
        return cout_total / total_products

    def __str__(self):  # CORRIGÉ : c'était "str" avant
        return self.nom
    
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, related_name='users')
    entrepot = models.ForeignKey('Entrepot', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    telephone = models.CharField(max_length=15, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)  # utile pour suivre les modifications

    def __str__(self):
        role_name = self.role.name if self.role else 'Aucun rôle'
        entrepot_name = self.entrepot.nom if self.entrepot else 'Aucun entrepôt'
        return f"{self.user.username} - {role_name} - {entrepot_name}"

    # Signal pour créer/modifier automatiquement le profil utilisateur
    @receiver(post_save, sender=User)
    def create_or_update_user_profile(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)
        else:
            instance.profile.save()

class DemandePrevision(models.Model):
    trimestre = models.IntegerField()
    annee = models.IntegerField()
    valeur = models.FloatField()

    class Meta:
        unique_together = ['trimestre', 'annee']

class ParametresStock(models.Model):
    stock_initial = models.FloatField(default=500)
    delai_livraison = models.IntegerField(default=2)  # en mois
    cout_passation_commande = models.FloatField(default=100)
    prix_unitaire = models.FloatField(default=20)
    taux_possession = models.FloatField(default=0.10)  # 10%
    stock_securite = models.FloatField(default=300)

class Product(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    entrepots = models.ForeignKey(Entrepot, on_delete=models.CASCADE)
    delai_reappro_moyen = models.IntegerField(default=7, help_text="Délai de réapprovisionnement moyen en jours")
    facteur_z = models.DecimalField(max_digits=4, decimal_places=2, default=1.96, 
                                   help_text="Facteur Z pour le niveau de service (1.96 = 97.5%)")
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('valide', 'Validé'),
            ('refuse', 'Refusé'),
            ('a_discuter', 'À discuter'),
            ('non_demande', 'Non demandé')
        ],
        default='non_demande'
    )

    def __str__(self):
        return self.name

    def calcul_stock_securite(self, ecart_type=None, delai_reappro=None, facteur_Z=None):
        """
        Calcule le stock de sécurité
        """
        if ecart_type is None:
            ecart_type = self.get_ecart_type_demande()
        if delai_reappro is None:
            delai_reappro = self.delai_reappro_moyen
        if facteur_Z is None:
            facteur_Z = float(self.facteur_z)
            
        return int(facteur_Z * ecart_type * math.sqrt(delai_reappro))
    
    def get_ecart_type_demande(self, periode_days=90):
        """
        Calcule l'écart type de la demande journalière sur une période donnée
        """
        date_debut = timezone.now() - timedelta(days=periode_days)
        
        # Grouper les sorties par jour et calculer les quantités journalières
        sorties_par_jour = {}
        sorties = self.sortie_set.filter(date_sortie__gte=date_debut)
        
        for sortie in sorties:
            date_key = sortie.date_sortie.date()
            if date_key not in sorties_par_jour:
                sorties_par_jour[date_key] = 0
            sorties_par_jour[date_key] += sortie.quantite
        
        # Créer une liste avec tous les jours (y compris ceux sans sortie = 0)
        demandes_journalieres = []
        date_courante = date_debut.date()
        while date_courante <= timezone.now().date():
            demandes_journalieres.append(sorties_par_jour.get(date_courante, 0))
            date_courante += timedelta(days=1)
        
        # Calculer l'écart type
        if len(demandes_journalieres) < 2:
            return 0
        
        moyenne = sum(demandes_journalieres) / len(demandes_journalieres)
        variance = sum((x - moyenne) ** 2 for x in demandes_journalieres) / (len(demandes_journalieres) - 1)
        return math.sqrt(variance)
    
    @property
    def stock_securite(self):
        """
        Property pour obtenir le stock de sécurité calculé
        """
        return self.calcul_stock_securite()
    
    @property
    def statut_stock(self):
        """
        Retourne le statut du stock par rapport au stock de sécurité
        """
        stock_sec = self.stock_securite
        if self.stock <= 0:
            return "rupture"
        elif self.stock <= stock_sec:
            return "critique"
        elif self.stock <= stock_sec * 1.5:
            return "bas"
        else:
            return "normal"
    
    @property
    def stock_display_info(self):
        """
        Retourne les informations d'affichage du stock avec le stock de sécurité
        """
        stock_sec = self.stock_securite
        statut = self.statut_stock
        
        return {
            'stock_actuel': self.stock,
            'stock_securite': stock_sec,
            'statut': statut,
            'message': self.get_stock_message(statut, stock_sec)
        }
    
    def get_stock_message(self, statut, stock_securite):
        """
        Génère un message approprié selon le statut du stock
        """
        if statut == "rupture":
            return f"RUPTURE - Stock de sécurité: {stock_securite}"
        elif statut == "critique":
            return f"CRITIQUE - En dessous du stock de sécurité ({stock_securite})"
        elif statut == "bas":
            return f"BAS - Stock de sécurité: {stock_securite}"
        else:
            return f"NORMAL - Stock de sécurité: {stock_securite}"
    
    def update_stock(self):
        """
        Recalcule le stock total basé sur tous les réapprovisionnements reçus
        moins toutes les sorties effectuées.
        Cette méthode garantit la cohérence des données.
        """
        # Calcul du total des réapprovisionnements REÇUS uniquement
        total_reappro = self.reapprovisionnement_set.filter(
            date_reception__isnull=False  # Seulement les réapprovisionnements reçus
        ).aggregate(
            total=models.Sum('quantite')
        )['total'] or 0
        
        # Calcul du total des sorties
        total_sorties = self.sortie_set.aggregate(
            total=models.Sum('quantite')
        )['total'] or 0
        
        # Calcul du nouveau stock
        nouveau_stock = total_reappro - total_sorties
        
        # Le stock ne peut jamais être négatif
        self.stock = max(0, nouveau_stock)
        
        # Sauvegarde uniquement le champ stock pour optimiser
        self.save(update_fields=['stock'])
        
        return self.stock
    
    def get_stock_details(self):
        """
        Retourne les détails du calcul du stock pour debugging/audit
        """
        total_reappro = self.reapprovisionnement_set.filter(
            date_reception__isnull=False
        ).aggregate(total=models.Sum('quantite'))['total'] or 0
        
        total_sorties = self.sortie_set.aggregate(
            total=models.Sum('quantite')
        )['total'] or 0
        
        return {
            'stock_actuel': self.stock,
            'total_reapprovisionnements': total_reappro,
            'total_sorties': total_sorties,
            'stock_calcule': max(0, total_reappro - total_sorties),
            'coherent': self.stock == max(0, total_reappro - total_sorties)
        }
    
    def verify_stock_integrity(self):
        """
        Vérifie si le stock stocké correspond au stock calculé
        Utile pour détecter les incohérences
        """
        details = self.get_stock_details()
        return details['coherent']    

    @property
    def taux_rotation_stocks(self):
        """Taux de rotation des stocks = (Coût des marchandises vendues / Stock moyen)"""
        # Vous devrez peut-être ajouter un champ pour le coût des marchandises vendues
        # ou le calculer à partir des sorties
        if self.stock == 0:
            return 0
        cout_ventes = sum(sortie.quantite * self.price for sortie in self.sortie_set.all())
        stock_moyen = self.stock  # Pour simplifier, on prend le stock actuel
        return cout_ventes / stock_moyen
    @property
    def taux_rupture(self, periode_days=30):
        """Taux de rupture = (Nombre de ruptures / Nombre total de commandes)"""
        # Vous aurez besoin d'un modèle pour suivre les commandes et les ruptures
        # Ceci est un exemple conceptuel
        total_orders = self.commandes.filter(date__gte=timezone.now()-timedelta(days=periode_days)).count()
        rupture_count = self.ruptures.filter(date__gte=timezone.now()-timedelta(days=periode_days)).count()
        return rupture_count / total_orders if total_orders > 0 else 0
    @property
    def couverture_stock(self):
        """Couverture de stock = (Stock disponible / Demande moyenne journalière)"""
        periode_days = 30  # Vous pouvez ajuster cette valeur ou la passer en paramètre
        date_debut = timezone.now() - timedelta(days=periode_days)
        total_demand = sum(
            sortie.quantite for sortie in 
            self.sortie_set.filter(date_sortie__gte=date_debut)
        )
        demande_moyenne_journaliere = total_demand / periode_days if periode_days > 0 else 0
        return self.stock / demande_moyenne_journaliere if demande_moyenne_journaliere > 0 else 0



class Reapprovisionnement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date_commande = models.DateTimeField()
    date_reception = models.DateTimeField()
    quantite = models.IntegerField()
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE)
    
    @property
    def delai_reapprovisionnement(self):
        """Calcule le délai en jours entre commande et réception"""
        if self.date_reception and self.date_commande:
            return (self.date_reception - self.date_commande).days
        return None
    
    @property
    def est_recu(self):
        """Indique si le réapprovisionnement a été reçu"""
        return self.date_reception is not None
    
    def marquer_comme_recu(self):
        """Marque le réapprovisionnement comme reçu à la date actuelle"""
        if not self.date_reception:
            self.date_reception = timezone.now()
            self.save()
            return True
        return False
    

    
class Sortie(models.Model):
    produit = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantite = models.IntegerField()
    remarque = models.TextField(blank=True)
    date_sortie = models.DateTimeField(auto_now_add=True)
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE, null=True, blank=True)
    motif_sortie = models.CharField(
        max_length=50,
        choices=[
            ('VENTE', 'Vente'),
            ('PERTE', 'Perte'),
            ('CASSE', 'Casse'),
            ('TRANSFERT', 'Transfert'),
            ('RETOUR', 'Retour'),
            ('AUTRE', 'Autre'),
        ],
        default='VENTE'
    )

    def __str__(self):
        return f"Sortie de {self.quantite} {self.produit.name} le {self.date_sortie.strftime('%Y-%m-%d')}"
    
    def clean(self):
        """Validation avant sauvegarde"""
        from django.core.exceptions import ValidationError
        if self.quantite <= 0:
            raise ValidationError("La quantité doit être positive")
        
        # Optionnel : vérifier si il y a assez de stock
        # (peut être désactivé selon vos besoins métier)
        if hasattr(self, 'produit') and self.produit:
            if self.quantite > self.produit.stock:
                raise ValidationError(
                    f"Stock insuffisant. Stock disponible: {self.produit.stock}, "
                    f"Quantité demandée: {self.quantite}"
                )
    

class UserLoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    def __str__(self):
        return f"{self.user.username} at {self.login_time}"
    



class ParametresEOQ(models.Model):
    taux_possession = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.15,
        help_text="Taux de possession annuel (ex: 0.15 pour 15%)"
    )
    cout_commande_defaut = models.DecimalField(
        max_digits=10, decimal_places=2, default=50,
        help_text="Coût fixe par commande par défaut"
    )
    
    class Meta:
        verbose_name = "Paramètres EOQ"
        verbose_name_plural = "Paramètres EOQ"


