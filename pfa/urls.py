from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    path('QOE_quantite/', views.QOE_quantite, name='QOE_quantite'),
    path('QOE_intervalle', views.QOE_intervalle , name='QOE_intervalle'),
    
    path('ajouter-demande/', views.ajouter_demande, name='ajouter_demande'),
    path('parametres/', views.modifier_parametres, name='modifier_parametres'),

    path('entrepots/', views.entrepot_list, name='entrepot_list'),
    path('entrepot/<int:pk>/', views.entrepot_detail, name='entrepot_detail'),
    path('entrepots/ajouter/', views.ajouter_entrepot, name='ajouter_entrepot'),
    path('entrepot/<int:pk>/edit/', views.edit_entrepot, name='edit_entrepot'),
    path('entrepot/<int:pk>/delete/', views.confirm_delete_entrepot, name='delete_entrepot'),


    path('products/', views.products , name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/delete/', views.confirm_delete_product, name='confirm_delete_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    
    path('register/', views.register_user, name='register'),
    path('users/', views.users, name='users'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('user/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.confirm_delete_user, name='confirm_delete_user'),


    path('sorties/', views.sortie_list, name='sortie_list'),
    path('sorties/add/', views.add_sortie, name='add_sortie'),
    path('sorties/<int:sortie_id>/', views.sortie_detail, name='sortie_detail'),
    path('sorties/<int:sortie_id>/edit/', views.edit_sortie, name='edit_sortie'),
    path('sorties/<int:sortie_id>/delete/', views.delete_sortie, name='delete_sortie'),

    path('reapprovisionnements/', views.reapprovisionnement_list, name='reapprovisionnement_list'),
    path('reapprovisionnements/add/', views.add_reapprovisionnement, name='add_reapprovisionnement'),
    path('reapprovisionnement/<int:pk>/edit/', views.edit_reapprovisionnement, name='edit_reapprovisionnement'),
    path('reapprovisionnement/<int:pk>/', views.reapprovisionnement_detail, name='reapprovisionnement_detail'),
    path('reapprovisionnement/<int:pk>/delete/', views.delete_reapprovisionnement, name='delete_reapprovisionnement'),


    path('produit/<int:product_id>/planification-eoq/', views.planification_eoq_produit, name='planification_eoq'),

    path('demander-validation/<int:product_id>/', views.demander_validation, name='demander_validation'),
    path('valider-produit/<int:product_id>/<str:action>/', views.valider_produit, name='valider_produit'),

    path('reinitialiser-validation/<int:product_id>/', views.reinitialiser_validation, name='reinitialiser_validation'),

]