# forms.py
from django import forms
from .models import DemandePrevision, ParametresStock,Role, Entrepot,UserProfile,Product,Sortie,Reapprovisionnement
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


    

class DemandePrevisionMatriceForm(forms.Form):
    annee_debut = forms.IntegerField(label="Année de début", min_value=2000, max_value=2100)
    nombre_annees = forms.IntegerField(label="Nombre d'années", min_value=1, max_value=5, initial=3)
    
    def get_tableau_matrice(self, annee_debut, nombre_annees):
        # Préparer la structure du tableau
        annees = range(annee_debut, annee_debut + nombre_annees)
        tableau = []
        
        # Récupérer les données existantes
        for annee in annees:
            ligne = {'annee': annee, 'trimestres': [None, None, None, None]}
            for i in range(4):
                try:
                    demande = DemandePrevision.objects.get(annee=annee, trimestre=i+1)
                    ligne['trimestres'][i] = demande.valeur
                except DemandePrevision.DoesNotExist:
                    pass
            tableau.append(ligne)
        
        return tableau
    
class ParametresStockForm(forms.ModelForm):
    class Meta:
        model = ParametresStock
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stock_securite'].required = False  # Le rendre optionnel

class DonneesForm(forms.Form):
    delai_reappro = forms.FloatField(
        label="Délai de réapprovisionnement (en mois)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    stock_initial = forms.IntegerField(
        label="Stock initial",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    stock_securite = forms.FloatField(
        required=False,
        label="Stock de sécurité (laisser vide pour le calcul automatique)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optionnel'})
    )
    taux_possession = forms.FloatField(
        label="Taux de possession (%)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    prix_unitaire = forms.FloatField(
        label="Prix unitaire",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    cout_passation = forms.FloatField(
        label="Coût de passation d'une commande",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock']
        exclude = ['entrepots']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class EntrepotForm(forms.ModelForm):
    class Meta:
        model = Entrepot
        fields = ['nom','ville', 'adresse', 'description','surface','cout_variable_unitaire','cout_fixe_annuel' ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'surface': forms.NumberInput(attrs={'class': 'form-control'}),
            'cout_variable_unitaire' : forms.NumberInput(attrs={'class': 'form-control'}),
            'cout_fixe_annuel' : forms.NumberInput(attrs={'class': 'form-control'}),
        }

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="",
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Adresse Email'})
    )
    first_name = forms.CharField(
        label="",
        max_length=100,
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Prénom'})
    )
    last_name = forms.CharField(
        label="",
        max_length=100,
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Nom'})
    )
    telephone = forms.CharField(
        label="",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Téléphone'})
    )
    role = forms.ModelChoiceField(
        label="Rôle",
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={'class':'form-control'})
    )
    entrepot = forms.ModelChoiceField(
        label="Entrepôt",
        queryset=Entrepot.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class':'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user', None)
        super(SignUpForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs['placeholder'] = "Nom d'utilisateur"
        self.fields['username'].label = ''
        self.fields['username'].help_text = '<span class="form-text text-muted"><small>Requis. 150 caractères maximum. Lettres, chiffres et @/./+/-/_ uniquement.</small></span>'

        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Mot de passe'
        self.fields['password1'].label = ''
        self.fields['password1'].help_text = '<ul class="form-text text-muted small"><li>Le mot de passe doit contenir au moins 8 caractères.</li><li>Le mot de passe ne peut pas être un mot de passe couramment utilisé.</li><li>Votre mot de passe ne peut pas être entièrement numérique.</li></ul>'

        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirmation du mot de passe'
        self.fields['password2'].label = ''
        self.fields['password2'].help_text = '<span class="form-text text-muted"><small>Entrez le même mot de passe que précédemment, pour vérification.</small></span>'

        if self.current_user and not self.current_user.is_superuser:
            try:
                user_profile = self.current_user.profile
                if user_profile.role.name != Role.ADMIN:
                    del self.fields['role']
            except:
                del self.fields['role']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

            user_profile, created = UserProfile.objects.get_or_create(user=user)

            if 'role' in self.cleaned_data:
                user_profile.role = self.cleaned_data['role']
            else:
                default_role, _ = Role.objects.get_or_create(name=Role.GESTIONNAIRE)
                user_profile.role = default_role

            user_profile.entrepot = self.cleaned_data.get('entrepot')
            user_profile.telephone = self.cleaned_data.get('telephone')
            user_profile.save()

        return user

class EditUserForm(forms.ModelForm):
    # Champs supplémentaires pas dans User mais dans UserProfile
    telephone = forms.CharField(max_length=15, required=False)
    role = forms.ModelChoiceField(queryset=Role.objects.all())
    entrepot = forms.ModelChoiceField(queryset=Entrepot.objects.all(), required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active')

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['telephone'].initial = profile.telephone
            self.fields['role'].initial = profile.role
            self.fields['entrepot'].initial = profile.entrepot

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile = user.profile
        profile.telephone = self.cleaned_data['telephone']
        profile.role = self.cleaned_data['role']
        profile.entrepot = self.cleaned_data['entrepot']
        if commit:
            profile.save()
        return user

class SortieForm(forms.ModelForm):
    class Meta:
        model = Sortie
        exclude = ['entrepot']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control'}),
            'remarque': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        user_entrepot = kwargs.pop('user_entrepot', None)
        super().__init__(*args, **kwargs)
        if user_entrepot:
            # Filtrer les produits par l'entrepôt du gestionnaire
            self.fields['produit'].queryset = Product.objects.filter(entrepots=user_entrepot)

class ReapprovisionnementForm(forms.ModelForm):
    class Meta:
        model = Reapprovisionnement
        fields = ['product', 'date_commande', 'date_reception', 'quantite', 'entrepot']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'date_commande': forms.DateTimeInput(attrs={'class': 'form-control','type': 'datetime-local'}),
            'date_reception': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        