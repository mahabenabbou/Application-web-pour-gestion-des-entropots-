import numpy as np

def demande(*annees_data):
    dem = []
    for donnees_annee in annees_data:
        dem.extend(donnees_annee)
    
    xi = np.array([i for i in range(1, len(dem) + 1)])
    
    x_mean = np.mean(xi) 
    dem_mean = np.mean(dem)
    
    numerateur = np.sum((xi - x_mean) * (dem - dem_mean))
    denominateur = np.sum((xi - x_mean) ** 2)
    
    a = numerateur / denominateur
    b = dem_mean - a * x_mean
    return dem, a, b

def calcul_coeff(Y, a, b):
    X = np.array([i for i in range(1, 13)])
    y_theorique = a * X + b
    Ci = Y / y_theorique
    coeff = [Ci[i::4].mean() for i in range(4)]
    return coeff

def predire_an(Y, a, b):
    x4 = np.array([13, 14, 15, 16])
    predictions = a * x4 + b
    coeff = calcul_coeff(Y, a, b)
    valeurY = [predictions[i] * coeff[i] for i in range(4)]
    return valeurY

def prediction_mois(Y4):
    previsions_mensuelle = []
    for prevision in Y4:
        valeur_mois = round(prevision / 3)
        previsions_mensuelle.extend([valeur_mois] * 3)
    return previsions_mensuelle

def calculer_livraisons(consommations, stock_initial, delai_mois):
    n = len(consommations)
    resultats = []
    stock = stock_initial
    
    for i in range(n):
        stock_apres_consommation = stock - consommations[i]

        if i % 3 == 0:
            livraison = consommations[i] + consommations[i+1] / 2 if i+1 < n else consommations[i]
            mois_commande = None
            mois_livraison = ("le 1 du mois", i + 1)
        elif i % 3 == 1:
            livraison = consommations[i+1] + consommations[i]/2 if i+1 < n else consommations[i]
            mois_commande = ("le 1 du mois", i + 1)
            mois_livraison = ("le 15 du mois", i + 1)
        else:
            livraison = 0
            mois_livraison = None
            mois_commande = ("le 15 du mois", i + 1)

        stock_rectifie = stock_apres_consommation + livraison
        
        resultats.append({
            "Mois": i + 1,
            "Consommation": consommations[i],
            "Livraison": livraison,
            "stock_apres_consommation": stock_apres_consommation,
            "stock_rectifie": stock_rectifie,
            "mois_commande": mois_commande,
            "mois_livraison": mois_livraison,
        })
        
        stock = stock_rectifie
    
    return resultats