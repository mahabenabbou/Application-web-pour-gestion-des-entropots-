# views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse,HttpResponseForbidden,HttpResponse
from .models import DemandePrevision, ParametresStock, Role, Entrepot, Product,UserProfile,Sortie,Reapprovisionnement
from .forms import ParametresStockForm, DemandePrevisionMatriceForm, DonneesForm, SignUpForm, ProductForm,EditUserForm,EntrepotForm,SortieForm,ReapprovisionnementForm
import math
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .utils.wilson import demande, predire_an, prediction_mois, calculer_livraisons
import numpy as np
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import UserLoginHistory
from django.db.models import F, ExpressionWrapper, DurationField, Avg
from datetime import datetime
from django.views.decorators.http import require_POST

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    UserLoginHistory.objects.create(user=user, ip_address=ip)



def role_required(*roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.profile.role.name in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied 
        return _wrapped_view
    return decorator

#login/logout/dashboard
@login_required
def home(request):
    user_profile = request.user.profile
    role = user_profile.role.name if user_profile.role else None
    context = {'role': role}

    if role == "directeur":
        
        products = Product.objects.all()
        kpi_products = []
        
        for product in products:
            kpi_products.append({
                'product': product,
                'taux_rotation': product.taux_rotation_stocks,  
                'couverture_stock': product.couverture_stock,   
            })
        
        delai_moyen = Reapprovisionnement.objects.annotate(
            delai=ExpressionWrapper(
                F('date_reception') - F('date_commande'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_delai=Avg('delai')
        )['avg_delai']
    
        delai_moyen_jours = delai_moyen.total_seconds() / 86400 if delai_moyen else 0
        entrepots = Entrepot.objects.all()
        kpi_entrepots = [{
            'entrepot': e,
            'cout_entreposage': e.cout_entreposage  
        } for e in entrepots]
        
        context.update({
            'kpi_products': kpi_products,
            'delai_moyen_reappro': delai_moyen_jours,
            'kpi_entrepots': kpi_entrepots,
        })
    
    elif role == "gestionnaire":
    # Récupération de l'entrepôt du gestionnaire
        entrepot = request.user.profile.entrepot
    
    # Filtrage des produits par entrepôt (correction de la requête)
        products = Product.objects.filter(entrepots=entrepot)
        kpi_products = []
        
        for product in products:
            kpi_products.append({
                'product': product,
                'taux_rotation': product.taux_rotation_stocks,  # Propriété
                'couverture_stock': product.couverture_stock,    # Propriété
            })
    
    # Calcul du délai moyen pour les réapprovisionnements de cet entrepôt
        delai_moyen = Reapprovisionnement.objects.filter(
            entrepot=entrepot
        ).annotate(
            delai=ExpressionWrapper(
                F('date_reception') - F('date_commande'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_delai=Avg('delai')
        )['avg_delai']
        
        # Conversion en jours
        delai_moyen_jours = delai_moyen.total_seconds() / 86400 if delai_moyen else 0
        
        # KPI pour l'entrepôt
        kpi_entrepots = {
            'entrepot': entrepot,
            'cout_entreposage': entrepot.cout_entreposage  # Propriété
        }
        
        context.update({
            'kpi_products': kpi_products,
            'delai_moyen_reappro': delai_moyen_jours,
            'kpi_entrepots': kpi_entrepots,
            'current_entrepot': entrepot,  # Utile pour le template
        })

    elif role == "admin":
        # Statistiques admin
        last_week = timezone.now() - timedelta(days=7)
        context.update({
            'total_users': User.objects.count(),
            'new_users': User.objects.filter(date_joined__gte=last_week).count(),
            'logins_last_week': UserLoginHistory.objects.filter(login_time__gte=last_week).count(),
            'login_entries': UserLoginHistory.objects.order_by('-login_time')[:10],
            'entrepots_count': Entrepot.objects.count(),
            'products_count': Product.objects.count(),
            })    
    return render(request, 'home.html', context)

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Bienvenue, dans l'application")
            return redirect('home')
        else:
            messages.error(request, "Le numéro d'entrepôt ou bien le mot de passe ne sont pas correcte essayer une autre fois")
            return redirect('login')
    else:
        return render(request, 'login.html', {})

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, "Vous êtes maintenant déconnecté")
    return redirect('login')



#gestion des produits 

@role_required('admin', 'directeur', 'gestionnaire')
@login_required
def products(request):
    if request.user.profile.role.name == 'gestionnaire':
        entrepot = request.user.profile.entrepot
        products = Product.objects.filter(entrepots=entrepot)
    else:
        products = Product.objects.all()
    return render(request, "products.html", {'products': products})

@role_required('gestionnaire')
@login_required    
def add_product(request):
    user_profile = request.user.profile
    if not user_profile.entrepot:
        return HttpResponse("Aucun entrepôt associé à votre profil", status=403)

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.entrepots = user_profile.entrepot  # Assignation directe
            product.save()  # Use .set() for M2M
            return redirect('products')
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request,"Votre modification a bien été enregistrée")
            return redirect('products')
        else:
            messages.error(request,"Désolé, Les données que vous utilisez sont invalides")
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'edit_product.html', {'form': form, 'product': product})

@login_required
def confirm_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.delete()
        return redirect('products')  # Retour à la liste des produits après suppression

    return render(request, 'confirm_delete_product.html', {'product': product})



#gestion de calcule 

def calcul_ecart_type(an1, an2, an3):
    # Merge all demands from 3 years
    dem = an1 + an2 + an3
    # Calculate standard deviation
    return np.std(dem)

def calcul_stock_securite(ecart_type, delai_reappro, facteur_Z=1.96):
    # Safety stock calculation
    return int(facteur_Z * ecart_type * math.sqrt(delai_reappro))

def get_demandes_annees(annee1, annee2, annee3):
    def get_valeurs(annee):
        return list(
            DemandePrevision.objects.filter(annee=annee).order_by('trimestre').values_list('valeur', flat=True)
        )
    return get_valeurs(annee1), get_valeurs(annee2), get_valeurs(annee3)

@login_required
def QOE_intervalle(request):
    # Get all historical data
    demandes = DemandePrevision.objects.all().order_by('annee', 'trimestre')
    parametres = ParametresStock.objects.first()
    
    if not parametres:
        parametres = ParametresStock.objects.create()
    
    # Organize data by year
    demandes_par_annee = {}
    for d in demandes:
        if d.annee not in demandes_par_annee:
            demandes_par_annee[d.annee] = [0, 0, 0, 0]
        demandes_par_annee[d.annee][d.trimestre-1] = d.valeur
    
    # Extract last 3 years if available
    annees_ordonnees = sorted(demandes_par_annee.keys(), reverse=True)
    
    resultats_previsions = None

    if len(annees_ordonnees) >= 2:  # Need at least 2 years for prediction
        # Prepare all historical data by year
        donnees_historiques = []
        for annee in annees_ordonnees:
            donnees_historiques.append(demandes_par_annee[annee])
        
        # Use Mayer method with all available data
        if len(donnees_historiques) >= 3:
            # Use last 3 years
            demN2 = donnees_historiques[-3]
            demN1 = donnees_historiques[-2]
            demN = donnees_historiques[-1]
            
            Y1, a1, b1 = demande(demN2, demN1, demN)
        else:
            # Adapt to work with only 2 years
            demN1 = donnees_historiques[-2]
            demN = donnees_historiques[-1]
            
            # Adapted call to demand function with only 2 years
            toutes_demandes = demN1 + demN
            xi = np.array([i for i in range(1, len(toutes_demandes)+1)])
            x_mean = np.mean(xi)
            dem_mean = np.mean(toutes_demandes)
            numerateur = np.sum((xi - x_mean) * (toutes_demandes - dem_mean))
            denominateur = np.sum((xi - x_mean)**2)
            a1 = numerateur / denominateur
            b1 = dem_mean - a1 * x_mean
            Y1 = toutes_demandes
        
        Y4 = predire_an(Y1, a1, b1)
        Y_mois = prediction_mois(Y4)
        
        resultats_previsions = calculer_livraisons(
            consommations=Y_mois,
            stock_initial=parametres.stock_initial,
            delai_mois=parametres.delai_livraison
        )

    if parametres:
        parametres.taux_possession_pourcentage = parametres.taux_possession * 100
    
    context = {
        'demandes': demandes,
        'parametres': parametres,
        'resultats': resultats_previsions,
        'annees': annees_ordonnees
    }
    
    return render(request, 'QOE_intervalle.html', context)

@login_required
def ajouter_demande(request):
    tableau = []
    annee_debut = 2022  # Default
    nombre_annees = 3   # Default
    
    if request.method == 'GET' and 'annee_debut' in request.GET:
        form = DemandePrevisionMatriceForm(request.GET)
        if form.is_valid():
            annee_debut = form.cleaned_data['annee_debut']
            nombre_annees = form.cleaned_data['nombre_annees']
    else:
        form = DemandePrevisionMatriceForm(initial={'annee_debut': annee_debut, 'nombre_annees': nombre_annees})
    
    tableau = form.get_tableau_matrice(annee_debut, nombre_annees)
    
    if request.method == 'POST' and 'save_matrix' in request.POST:
        # Process submitted data
        try:
            for annee in range(annee_debut, annee_debut + nombre_annees):
                for trimestre in range(1, 5):
                    valeur_key = f"valeur_{annee}_{trimestre}"
                    if valeur_key in request.POST and request.POST[valeur_key].strip():
                        valeur = float(request.POST[valeur_key])
                        
                        # Update or create entry
                        demande, created = DemandePrevision.objects.update_or_create(
                            annee=annee,
                            trimestre=trimestre,
                            defaults={'valeur': valeur}
                        )
            
            messages.success(request, "Les données ont été enregistrées avec succès.")
            return redirect('QOE_intervalle')
        except ValueError:
            messages.error(request, "Erreur: Veuillez entrer des valeurs numériques valides.")
    
    context = {
        'form': form,
        'tableau': tableau,
        'annee_debut': annee_debut,
        'nombre_annees': nombre_annees,
    }
    
    return render(request, 'ajouter_demande.html', context)

@login_required
def modifier_parametres(request):
    parametres = ParametresStock.objects.first()
    if not parametres:
        parametres = ParametresStock.objects.create()

    if request.method == 'POST':
        form = ParametresStockForm(request.POST, instance=parametres)
        if form.is_valid():
            parametres = form.save(commit=False)

            # Check if field was left empty
            stock_securite_user_input = form.cleaned_data.get('stock_securite')

            if stock_securite_user_input in [None, '']:  # Empty field
                # Calculate automatically
                an1, an2, an3 = get_demandes_annees(2022, 2023, 2024)
                if an1 and an2 and an3:
                    ecart_type = calcul_ecart_type(an1, an2, an3)
                    delai = parametres.delai_livraison or 1
                    parametres.stock_securite = calcul_stock_securite(ecart_type, delai)
            else:
                # Otherwise keep user-entered value
                parametres.stock_securite = stock_securite_user_input

            parametres.save()
            return redirect('QOE_intervalle')
    else:
        form = ParametresStockForm(instance=parametres)

    return render(request, 'parametres.html', {'form': form})

def prevision_demande(an1, an2, an3):
    dem = an1 + an2 + an3
    xi = np.array([i for i in range(1, len(dem) + 1)])
    dem = np.array(dem)
    x_mean = np.mean(xi)
    dem_mean = np.mean(dem)
    numerateur = np.sum((xi - x_mean) * (dem - dem_mean))
    denominateur = np.sum((xi - x_mean) ** 2)
    a = numerateur / denominateur
    b = dem_mean - a * x_mean

    xi_n1 = [13, 14, 15, 16]  # Quarters of year N+1
    yitheo = [a * x + b for x in xi_n1]
    coeffs = [(yitheo[i] / np.mean(yitheo)) for i in range(4)]
    yiprev = [yitheo[i] * coeffs[i] for i in range(4)]
    
    return yiprev, sum(yiprev), coeffs

def methode_wilson(consommation_annuelle, cout_commande, prix_unitaire, taux_possession):
    # Economic order quantity calculation (Q)
    Q = math.sqrt((2 * consommation_annuelle * cout_commande) / (prix_unitaire * taux_possession))
    return Q

@login_required
def QOE_quantite(request):
    if request.method == "POST":
        form = DonneesForm(request.POST)
        
        # Get historical data
        an1 = []
        an2 = []
        an3 = []
        
        for trimestre in range(1, 5):
            try:
                an1.append(float(request.POST.get(f'an1_T{trimestre}', 0)))
                an2.append(float(request.POST.get(f'an2_T{trimestre}', 0)))
                an3.append(float(request.POST.get(f'an3_T{trimestre}', 0)))
            except (ValueError, TypeError):
                an1.append(0)
                an2.append(0)
                an3.append(0)
        
        if form.is_valid():
            delai_reappro = form.cleaned_data['delai_reappro']
            stock_initial = form.cleaned_data['stock_initial']
            stock_securite = form.cleaned_data['stock_securite']
            taux_possession = form.cleaned_data['taux_possession'] / 100
            prix_unitaire = form.cleaned_data['prix_unitaire']
            cout_passation = form.cleaned_data['cout_passation']
            
            # Calculate predictions
            prev_n1, C, coeffs = prevision_demande(an1, an2, an3)
            
            # Calculate standard deviation
            ecart_type = calcul_ecart_type(an1, an2, an3)

            # If safety stock not provided, calculate it
            if stock_securite is None:
                SS = calcul_stock_securite(ecart_type, delai_reappro)
            else:
                SS = stock_securite
            
            # Calculate Q (optimal order quantity)
            Q = methode_wilson(C, cout_passation, prix_unitaire, taux_possession)
            
            # Calculate number of orders and cadence
            nombre_de_commandes = C / Q
            cadence_mois = 12 / nombre_de_commandes  # in months
            
            # ==== REPLENISHMENT PROGRAM ====
            stock_programme = {}
            stock_actuel = stock_initial
            consommation_mensuelle = C / 12  # Average monthly consumption
            point_de_commande = SS + (consommation_mensuelle * delai_reappro)
            
            mois_annee = [
                            "1er janvier",
                            "1er février",
                            "1er mars",
                            "1er avril",
                            "1er mai",
                            "1er juin",
                            "1er juillet",
                            "1er août",
                            "1er septembre",
                            "1er octobre",
                            "1er novembre",
                            "1er décembre"
                        ]
            for mois in range(1, 13):  # Simulation over 12 months
                stock_actuel -= consommation_mensuelle
                
                # If stock reaches order point, place an order
                if stock_actuel <= point_de_commande:
                    stock_actuel += int(Q)+1  # Delivery after delay (simplified)
                    stock_programme[mois] = [mois_annee[mois-1],int(Q)+1, int(stock_actuel)]
                else:
                    stock_programme[mois] = [mois_annee[mois-1],None, int(stock_actuel)]

            # Prepare data for template
            donnees_historiques = {
                'an1': an1,
                'an2': an2,
                'an3': an3
            }

            return render(request, 'QOE_quantite.html', {
                'form': form,
                'prev_n1': [int(prev)+1 for prev in prev_n1] if prev_n1 else None,
                'C': int(C)+1,
                'coeffs': [float(coeff) for coeff in coeffs],
                'Q': round(float(Q)),
                'SS': round(float(SS)),
                'nombre_de_commandes': int(nombre_de_commandes)+ 1,
                'cadence_mois': round(float(cadence_mois), 1),
                'stock_initial': float(stock_initial),
                'stock_programme': stock_programme,
                'donnees_historiques': donnees_historiques,
            })
    else:
        form = DonneesForm()
        donnees_historiques = {
            'an1': [0, 0, 0, 0],
            'an2': [0, 0, 0, 0],
            'an3': [0, 0, 0, 0]
        }
    
    return render(request, 'QOE_quantite.html', {
        'form': form,
        'donnees_historiques': donnees_historiques
    })




#gestion des utilisateurs
@login_required
def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès!")
            return redirect('users')
    else:
        form = SignUpForm(user=request.user)
    
    return render(request, 'register.html', {'form': form})

@login_required
def users(request):
    # Check if user is admin or director
    try:
        user_profile = request.user.profile
        is_admin = user_profile.role.name == Role.ADMIN
        is_directeur = user_profile.role.name == Role.DIRECTEUR
    except:
        is_admin = False
        is_directeur = False
    
    # If user is admin, they see all users
    if is_admin or request.user.is_superuser or is_directeur:
        users = User.objects.all().exclude(id=request.user.id)
    # If user is director, they see managers
    else:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour voir la liste des utilisateurs.")
        return redirect('home')
    
    return render(request, 'users.html', {'users': users})

def user_detail(request, user_id):
    # On récupère l'utilisateur (ou 404 si pas trouvé)
    user = get_object_or_404(User, id=user_id)
    
    # On récupère le profil lié (avec gestion d'erreur si profil absent)
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None  # Ou tu peux gérer ça différemment (ex: créer un profil)
    
    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'user_detail.html', context)

@login_required
def edit_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=user_obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil utilisateur mis à jour avec succès.")
            return redirect('user_detail', user_id=user_obj.id)
    else:
        form = EditUserForm(instance=user_obj, user=request.user)

    context = {
        'form': form,
        'user_obj': user_obj,
    }
    return render(request, 'edit_user.html', context)

def confirm_delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        # Supprimer l'utilisateur
        user.delete()
        messages.success(request, f"L'utilisateur {user.username} a été supprimé avec succès.")
        return redirect('users')  # Mettre ici la vue/listing après suppression

    # Sinon afficher la page de confirmation
    return render(request, 'confirm_delete_user.html', {'user': user})






#gestion des entropots
@role_required('directeur')
@login_required
def entrepot_list(request):
    # Check user role
    try:
        user_profile = request.user.profile
        role = user_profile.role.name
    except:
        role = None
    
    # Define accessible warehouses according to role
    if role == Role.ADMIN or request.user.is_superuser:
        # Admin sees all warehouses
        entrepots = Entrepot.objects.all()
    elif role == Role.DIRECTEUR:
        # Director sees all warehouses
        entrepots = Entrepot.objects.all()
    elif role == Role.GESTIONNAIRE:
        # Manager sees only their warehouse
        entrepots = Entrepot.objects.filter(id=user_profile.entrepot.id) if user_profile.entrepot else Entrepot.objects.none()
    else:
        messages.error(request, "Vous n'avez pas les permissions nécessaires.")
        return redirect('home')
    
    return render(request, 'entrepot_list.html', {'entrepots': entrepots})

@role_required('directeur')
@login_required
def ajouter_entrepot(request):
    if request.method == 'POST':
        form = EntrepotForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('entrepot_list')  # tu définiras cette vue ensuite
    else:
        form = EntrepotForm()
    return render(request, 'ajouter_entrepot.html', {'form': form})

@role_required('directeur')
@login_required
def edit_entrepot(request, pk):
    entrepot = get_object_or_404(Entrepot, id=pk)
    if request.method == 'POST':
        form = EntrepotForm(request.POST, instance=entrepot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entrepôt modifié avec succès.')
            return redirect('entrepot_list')
    else:
        form = EntrepotForm(instance=entrepot)

    return render(request, 'edit_entrepot.html', {'form': form, 'entrepot': entrepot})

@role_required('directeur')
@login_required
def confirm_delete_entrepot(request, pk):
    entrepot = get_object_or_404(Entrepot, pk=pk)
    
    if request.method == 'POST':
        entrepot.delete()
        return redirect('entrepot_list')  # Redirige vers la liste des entrepôts
    
    return render(request, 'confirm_delete_entrepot.html', {'entrepot': entrepot})

@role_required('directeur')
@login_required
def entrepot_detail(request, pk):
    entrepot = get_object_or_404(Entrepot, pk=pk)
    return render(request, 'entrepot_detail.html', {'entrepot': entrepot})




#gestion des sorties 
@role_required('admin', 'directeur', 'gestionnaire')
def sortie_list(request):
    if request.user.profile.role.name == 'gestionnaire':
        entrepot = request.user.profile.entrepot
        sorties = Sortie.objects.filter(entrepot=entrepot)
    else:
        sorties = Sortie.objects.all()
    return render(request, 'sortie_list.html', {'sorties': sorties})

@role_required('gestionnaire')
@login_required
def add_sortie(request):
    user_profile = request.user.profile
    if not user_profile.entrepot:
        return HttpResponse("Aucun entrepôt associé à votre profil", status=403)

    if request.method == 'POST':
        form = SortieForm(request.POST, user_entrepot=user_profile.entrepot)
        if form.is_valid():
            sortie = form.save(commit=False)
            sortie.entrepot = user_profile.entrepot
            sortie.save()
            return redirect('sortie_list')
    else:
        form = SortieForm(user_entrepot=user_profile.entrepot)

    return render(request, 'sortie_add.html', {'form': form})

@login_required
def sortie_detail(request, sortie_id):
    sortie = get_object_or_404(Sortie, id=sortie_id)
    return render(request, 'sortie_detail.html', {'sortie': sortie})

@login_required
def edit_sortie(request, sortie_id):
    sortie = get_object_or_404(Sortie, id=sortie_id)
    if request.method == 'POST':
        form = SortieForm(request.POST, instance=sortie)
        if form.is_valid():
            form.save()
            return redirect('sortie_list')  # redirection vers la liste
    else:
        form = SortieForm(instance=sortie)
    return render(request, 'edit_sortie.html', {'form': form, 'sortie': sortie})

@login_required
def delete_sortie(request, sortie_id):
    sortie = get_object_or_404(Sortie, id=sortie_id)
    if request.method == 'POST':
        sortie.delete()
        return redirect('sortie_list')
    return render(request, 'delete_sortie_confirm.html', {'sortie': sortie})




def reapprovisionnement_list(request):
    user_profile = request.user.profile
    role = user_profile.role.name.lower()

    if role == "directeur":
        reapprovisionnements = Reapprovisionnement.objects.all()
    elif role == "gestionnaire":
        reapprovisionnements = Reapprovisionnement.objects.filter(entrepot=user_profile.entrepot)
    else:
        reapprovisionnements = Reapprovisionnement.objects.none()

    return render(request, 'reapprovisionnement_list.html', {'reapprovisionnements': reapprovisionnements})

def add_reapprovisionnement(request):
    user_profile = request.user.profile
    role = user_profile.role.name.lower()

    if request.method == 'POST':
        form = ReapprovisionnementForm(request.POST)
        if form.is_valid():
            reappro = form.save(commit=False)
            # Si gestionnaire : fixer l'entrepôt à celui du user
            if role == "gestionnaire":
                reappro.entrepot = user_profile.entrepot
            reappro.save()
            return redirect('reapprovisionnement_list')
    else:
        form = ReapprovisionnementForm()

    return render(request, 'reapprovisionnement_add.html', {'form': form})

@login_required
def edit_reapprovisionnement(request, pk):
    reappro = get_object_or_404(Reapprovisionnement, pk=pk)

    if request.method == 'POST':
        form = ReapprovisionnementForm(request.POST, instance=reappro)
        if form.is_valid():
            form.save()
            return redirect('reapprovisionnement_list')  # à adapter selon ta vue d'affichage
    else:
        form = ReapprovisionnementForm(instance=reappro)

    return render(request, 'edit_reaprovisionnement.html', {'form': form, 'reappro': reappro})

@login_required
def reapprovisionnement_detail(request, pk):
    reappro = get_object_or_404(Reapprovisionnement, pk=pk)
    return render(request, 'reapprovisionnement_detail.html', {'reappro': reappro})

@login_required
def delete_reapprovisionnement(request, pk):
    reappro = get_object_or_404(Reapprovisionnement, pk=pk)
    if request.method == 'POST':
        reappro.delete()
        messages.success(request, "Réapprovisionnement supprimé avec succès.")
        return redirect('reapprovisionnement_list')
    return render(request, 'confirm_delete_reapprovisionnement.html', {'reappro': reappro})



#try

@login_required
def planification_eoq_produit(request, product_id):
    """
    Vue pour générer la planification EOQ d'un produit pour l'année N+1
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Paramètres par défaut (vous pouvez les ajuster ou les mettre en base)
    TAUX_POSSESSION = 0.15  # 15% par an
    COUT_COMMANDE = 50  # Coût fixe par commande
    
    # 1. Calculer la demande annuelle basée sur l'historique
    demande_annuelle = calculer_demande_annuelle_prevue(product)
    
    if demande_annuelle == 0:
        context = {
            'product': product,
            'error': 'Pas assez de données historiques pour calculer la planification EOQ'
        }
        return render(request, 'planification_eoq.html', context)
    
    # 2. Calculer EOQ
    cout_unitaire = float(product.price)
    eoq = calculer_eoq(demande_annuelle, COUT_COMMANDE, cout_unitaire, TAUX_POSSESSION)
    
    # 3. Calculer les paramètres de planification
    nombre_commandes_annuel = math.ceil(demande_annuelle / eoq)
    intervalle_commandes_jours = 365 / nombre_commandes_annuel
    
    # 4. Générer le planning de l'année N+1
    planning = generer_planning_annuel(
        product, 
        eoq, 
        nombre_commandes_annuel, 
        intervalle_commandes_jours,
        demande_annuelle
    )
    
    # 5. Calculer les coûts
    couts = calculer_couts_eoq(demande_annuelle, eoq, COUT_COMMANDE, cout_unitaire, TAUX_POSSESSION)
    
    context = {
        'product': product,
        'demande_annuelle': demande_annuelle,
        'eoq': eoq,
        'nombre_commandes': nombre_commandes_annuel,
        'intervalle_jours': round(intervalle_commandes_jours, 1),
        'planning': planning,
        'couts': couts,
        'parametres': {
            'taux_possession': TAUX_POSSESSION * 100,
            'cout_commande': COUT_COMMANDE,
            'cout_unitaire': cout_unitaire
        }
    }
    
    return render(request, 'planification_eoq.html', context)


def calculer_demande_annuelle_prevue(product):
    """
    Calcule la demande annuelle prévue basée sur l'historique des sorties
    Utilise une moyenne mobile pondérée sur les 12 derniers mois
    """
    from django.utils import timezone
    
    # Récupérer les sorties des 24 derniers mois pour avoir assez de données
    date_limite = timezone.now() - timedelta(days=730)
    sorties = product.sortie_set.filter(
        date_sortie__gte=date_limite,
        motif_sortie='VENTE'  # Seulement les ventes
    ).order_by('date_sortie')
    
    if not sorties.exists():
        return 0
    
    # Grouper par mois
    demandes_mensuelles = {}
    for sortie in sorties:
        mois_key = sortie.date_sortie.strftime('%Y-%m')
        if mois_key not in demandes_mensuelles:
            demandes_mensuelles[mois_key] = 0
        demandes_mensuelles[mois_key] += sortie.quantite
    
    # Prendre les 12 derniers mois complets
    mois_ordonnes = sorted(demandes_mensuelles.keys(), reverse=True)
    if len(mois_ordonnes) >= 12:
        demandes_12_mois = [demandes_mensuelles[mois] for mois in mois_ordonnes[:12]]
    else:
        # Si moins de 12 mois, extrapoler
        demandes_disponibles = [demandes_mensuelles[mois] for mois in mois_ordonnes]
        moyenne_mensuelle = sum(demandes_disponibles) / len(demandes_disponibles)
        demandes_12_mois = demandes_disponibles + [moyenne_mensuelle] * (12 - len(demandes_disponibles))
    
    # Appliquer une pondération (mois récents plus importants)
    poids = [1.2, 1.15, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65]
    demande_ponderee = sum(d * p for d, p in zip(demandes_12_mois, poids))
    total_poids = sum(poids)
    
    return round(demande_ponderee / total_poids * 12)


def calculer_eoq(demande_annuelle, cout_commande, cout_unitaire, taux_possession):
    """
    Calcule la quantité économique de commande (EOQ)
    EOQ = √(2 × D × S / H)
    où D = demande annuelle, S = coût de commande, H = coût de possession
    """
    cout_possession = cout_unitaire * taux_possession
    eoq = math.sqrt((2 * demande_annuelle * cout_commande) / cout_possession)
    return round(eoq)


def generer_planning_annuel(product, eoq, nombre_commandes, intervalle_jours, demande_annuelle):
    """
    Génère le planning des commandes pour l'année N+1
    """
    from django.utils import timezone
    
    planning = []
    stock_actuel = product.stock
    demande_mensuelle = demande_annuelle / 12
    
    # Date de début (1er janvier de l'année prochaine)
    annee_prochaine = timezone.now().year + 1
    date_courante = datetime(annee_prochaine, 1, 1)
    
    for i in range(nombre_commandes):
        # Date de commande
        date_commande = date_courante + timedelta(days=i * intervalle_jours)
        
        # Date de réception (commande + délai)
        date_reception = date_commande + timedelta(days=product.delai_reappro_moyen)
        
        # Stock prévisionnel au moment de la commande
        mois_ecoules = (date_commande - datetime(annee_prochaine, 1, 1)).days / 30.44
        consommation_prevue = mois_ecoules * demande_mensuelle
        stock_previsionnel = max(0, product.stock + (i * eoq) - consommation_prevue)
        
        planning.append({
            'numero_commande': i + 1,
            'date_commande': date_commande.strftime('%d/%m/%Y'),
            'date_reception': date_reception.strftime('%d/%m/%Y'),
            'quantite': eoq,
            'stock_avant_commande': round(stock_previsionnel),
            'stock_after_reception': round(stock_previsionnel + eoq),
            'mois': date_commande.strftime('%B %Y')
        })
    
    return planning


def calculer_couts_eoq(demande_annuelle, eoq, cout_commande, cout_unitaire, taux_possession):
    """
    Calcule les différents coûts associés à la politique EOQ
    """
    nombre_commandes = demande_annuelle / eoq
    
    # Coût de commande annuel
    cout_commande_annuel = nombre_commandes * cout_commande
    
    # Coût de possession annuel
    stock_moyen = eoq / 2
    cout_possession_annuel = stock_moyen * cout_unitaire * taux_possession
    
    # Coût total de gestion des stocks
    cout_total_gestion = cout_commande_annuel + cout_possession_annuel
    
    # Coût d'achat annuel
    cout_achat_annuel = demande_annuelle * cout_unitaire
    
    return {
        'cout_commande_annuel': round(cout_commande_annuel, 2),
        'cout_possession_annuel': round(cout_possession_annuel, 2),
        'cout_total_gestion': round(cout_total_gestion, 2),
        'cout_achat_annuel': round(cout_achat_annuel, 2),
        'stock_moyen': round(stock_moyen),
        'nombre_commandes': round(nombre_commandes, 1)
    }

@login_required
def demander_validation(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.user.profile.role.name == 'gestionnaire':
        product.validation_status = 'en_attente'
        product.save()
    return redirect('products')  # Ou la page où est ta table

@login_required
def valider_produit(request, product_id, action):
    product = get_object_or_404(Product, pk=product_id)
    if request.user.profile.role.name == 'directeur':
        product.validation_status = action
        product.save()
    return redirect('products')

@login_required
def reinitialiser_validation(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    # Optionnel : tu peux ajouter un contrôle de rôle
    if request.user.profile.role.name in ['gestionnaire', 'directeur']:
        product.validation_status = 'non_demande'
        product.save()
    return redirect('products')  # ou la bonne URL