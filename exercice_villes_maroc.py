"""
============================================================
🚗 EXERCICE: Navigation Autonome entre Villes Marocaines
============================================================
Problème: Se rendre de Rabat (R) à Marrakech (M) en minimisant
la distance parcourue.

Basé sur le graphe du réseau routier simplifié du Maroc.
============================================================
"""

from problem_solving_agent import (
    NavigationProblem,
    SearchStrategy,
    ProblemSolvingAgent,
    NavigationPercept
)

# ============================================================
# EXERCICE 1 - CONSTRUCTION DU GRAPHE
# ============================================================

# 1. Création du graphe graph_villes_maroc (dict)
# Légende des villes:
#   R   = Rabat (État initial)
#   C   = Casablanca
#   A   = El Jadida/Azemmour
#   Ess = Essaouira
#   Me  = Meknès
#   Kh  = Khénifra/Khouribga
#   BM  = Beni Mellal
#   M   = Marrakech (État but)

graph_villes_maroc = {
    "R": {"C": 88, "Me": 140},                          # Rabat
    "C": {"R": 88, "A": 170, "Kh": 120},                # Casablanca
    "A": {"C": 170, "Ess": 170},                        # El Jadida/Azemmour
    "Ess": {"A": 170, "M": 180},                        # Essaouira
    "Me": {"R": 140, "Kh": 180, "BM": 200},             # Meknès
    "Kh": {"C": 120, "Me": 180, "A": 230, "M": 320, "BM": 140},  # Khénifra/Khouribga
    "BM": {"Me": 200, "Kh": 140, "M": 190},             # Beni Mellal
    "M": {"Ess": 180, "Kh": 320, "BM": 190}             # Marrakech
}

# Définition des états
ETAT_INITIAL = "R"   # Rabat
ETAT_BUT = "M"       # Marrakech

print("=" * 60)
print("🗺️  GRAPHE DES VILLES MAROCAINES")
print("=" * 60)
print(f"\n📍 État initial: {ETAT_INITIAL} (Rabat)")
print(f"🎯 État but: {ETAT_BUT} (Marrakech)")
print(f"\n📊 Graphe des connexions:")
for ville, voisins in graph_villes_maroc.items():
    print(f"   {ville}: {voisins}")

# ============================================================
# EXERCICE 2 - CRÉATION DU PROBLÈME
# ============================================================

print("\n" + "=" * 60)
print("📝 EXERCICE 1.2: CRÉATION DU PROBLÈME")
print("=" * 60)

# Instanciation du problème de navigation
problem = NavigationProblem(
    initial_state=ETAT_INITIAL,  # R (Rabat)
    goal=ETAT_BUT,               # M (Marrakech)
    graph=graph_villes_maroc
)

print(f"\n✅ Problème créé avec succès!")
print(f"   - État initial: {problem.initial_state}")
print(f"   - État but: {problem.goal_state}")

# ============================================================
# EXERCICE 3 - VALIDATION DU PROBLÈME
# ============================================================

print("\n" + "=" * 60)
print("🔍 EXERCICE 1.3: VALIDATION DU PROBLÈME")
print("=" * 60)

# Test 1: Actions possibles depuis une ville
print("\n📍 Test 1: Actions possibles depuis chaque ville")
print("-" * 50)
for ville in graph_villes_maroc.keys():
    actions = problem.actions(ville)
    print(f"   Depuis {ville}: {actions}")

# Test 2: Test du but
print("\n🎯 Test 2: Test du but (goal_test)")
print("-" * 50)
villes_test = ["R", "C", "Me", "Kh", "M"]
for ville in villes_test:
    est_but = problem.goal_test(ville)
    symbole = "✅" if est_but else "❌"
    print(f"   {ville} est le but? {symbole} {est_but}")

# Test 3: Successeurs d'une ville intermédiaire
print("\n🔗 Test 3: Successeurs des villes intermédiaires")
print("-" * 50)
villes_intermediaires = ["C", "Me", "Kh", "BM"]
for ville in villes_intermediaires:
    successeurs = problem.get_successors(ville)
    print(f"   Successeurs de {ville}:")
    for succ, cout in successeurs:
        print(f"      → {succ} (distance: {cout} km)")

# ============================================================
# EXERCICE 2 - RECHERCHE AVEUGLE (DFS, BFS, UCS)
# ============================================================

print("\n" + "=" * 60)
print("📝 EXERCICE 2: RECHERCHE AVEUGLE")
print("=" * 60)

print("""
Les algorithmes de recherche aveugle explorent le graphe sans
utiliser d'information sur la distance au but:

🔵 BFS (Breadth-First Search): Explore niveau par niveau
   - Complet: OUI
   - Optimal: OUI (si coûts uniformes)
   
🟢 DFS (Depth-First Search): Explore en profondeur d'abord
   - Complet: NON (peut boucler)
   - Optimal: NON
   
🟡 UCS (Uniform Cost Search): Explore par coût croissant
   - Complet: OUI
   - Optimal: OUI (pour tout type de coûts)
""")

# 2.1 - DFS (Depth-First Search)
print("\n" + "-" * 60)
print("🟢 2.1 - RECHERCHE EN PROFONDEUR (DFS)")
print("-" * 60)
print("Principe: Explore le plus profondément possible avant de revenir")
path_dfs = SearchStrategy.dfs(problem)

# 2.2 - BFS (Breadth-First Search)
print("\n" + "-" * 60)
print("🔵 2.2 - RECHERCHE EN LARGEUR (BFS)")
print("-" * 60)
print("Principe: Explore tous les voisins avant de passer au niveau suivant")
path_bfs = SearchStrategy.bfs(problem)

# 2.3 - UCS (Uniform Cost Search)
print("\n" + "-" * 60)
print("🟡 2.3 - RECHERCHE À COÛT UNIFORME (UCS)")
print("-" * 60)
print("Principe: Explore toujours le noeud avec le coût cumulé le plus faible")
path_ucs = SearchStrategy.ucs(problem)

# ============================================================
# EXERCICE 3 - HEURISTIQUE & A*
# ============================================================

print("\n" + "=" * 60)
print("📝 EXERCICE 3: HEURISTIQUE & A*")
print("=" * 60)

# 3.1 - Proposition d'heuristiques admissibles
print("\n" + "-" * 60)
print("📊 3.1 - PROPOSITION D'HEURISTIQUES ADMISSIBLES")
print("-" * 60)

print("""
Une heuristique h(n) est ADMISSIBLE si elle ne surestime jamais
le coût réel pour atteindre le but: h(n) ≤ h*(n)

Pour le problème des villes marocaines, on peut utiliser:
- La distance à vol d'oiseau (euclidienne) vers Marrakech
- Cette distance est toujours ≤ à la distance routière réelle
""")

# Heuristiques (distances à vol d'oiseau vers Marrakech)
heuristics_marrakech = {
    "R": 320,    # Rabat - distance à vol d'oiseau vers Marrakech
    "C": 240,    # Casablanca
    "A": 200,    # El Jadida/Azemmour
    "Ess": 150,  # Essaouira
    "Me": 280,   # Meknès
    "Kh": 200,   # Khénifra/Khouribga
    "BM": 150,   # Beni Mellal
    "M": 0       # Marrakech (but)
}

print("Heuristiques proposées (distance à vol d'oiseau vers Marrakech):")
print("-" * 50)
for ville, h in heuristics_marrakech.items():
    print(f"   h({ville:3}) = {h:3} km")

# 3.2 - Vérification de l'admissibilité
print("\n" + "-" * 60)
print("✅ 3.2 - VÉRIFICATION DE L'ADMISSIBILITÉ")
print("-" * 60)

print("""
Pour vérifier l'admissibilité, on compare h(n) avec le coût réel
optimal h*(n) obtenu par UCS:
""")

# Calculer le coût réel optimal pour chaque ville vers M
def calculer_cout_optimal(graph, depart, arrivee):
    """Calcule le coût optimal de depart vers arrivee avec UCS"""
    import heapq
    if depart == arrivee:
        return 0

    frontier = [(0, depart)]
    explored = set()

    while frontier:
        cost, state = heapq.heappop(frontier)
        if state == arrivee:
            return cost
        if state in explored:
            continue
        explored.add(state)
        for neighbor, edge_cost in graph.get(state, {}).items():
            if neighbor not in explored:
                heapq.heappush(frontier, (cost + edge_cost, neighbor))
    return float('inf')

print(f"{'Ville':<6} {'h(n)':<8} {'h*(n)':<10} {'h(n) ≤ h*(n)?':<15} {'Admissible?'}")
print("-" * 55)

toutes_admissibles = True
for ville in heuristics_marrakech:
    h_n = heuristics_marrakech[ville]
    h_star = calculer_cout_optimal(graph_villes_maroc, ville, "M")
    admissible = h_n <= h_star
    if not admissible:
        toutes_admissibles = False
    symbole = "✅ OUI" if admissible else "❌ NON"
    comparaison = f"{h_n} ≤ {h_star}" if h_star != float('inf') else f"{h_n} ≤ ∞"
    print(f"{ville:<6} {h_n:<8} {h_star:<10} {comparaison:<15} {symbole}")

print()
if toutes_admissibles:
    print("🎯 CONCLUSION: Toutes les heuristiques sont ADMISSIBLES!")
    print("   → A* est garanti de trouver le chemin optimal.")
else:
    print("⚠️  ATTENTION: Certaines heuristiques ne sont pas admissibles!")

# 3.3 - Exécution de A*
print("\n" + "-" * 60)
print("🔴 3.3 - EXÉCUTION DE A*")
print("-" * 60)
print("Principe: f(n) = g(n) + h(n)")
print("   g(n) = coût réel depuis le départ")
print("   h(n) = estimation du coût vers le but (heuristique)")
print()

print("\n" + "-" * 60)
print("🔴 4. RECHERCHE A* (A-STAR)")
print("-" * 60)
path_astar = SearchStrategy.a_star(problem, heuristics_marrakech)

# ============================================================
# EXERCICE 4 - COMPARAISON DES CHEMINS
# ============================================================

def calculer_cout_chemin(chemin, graph):
    """Calcule le coût total d'un chemin"""
    if not chemin or len(chemin) < 2:
        return 0
    cout = 0
    for i in range(len(chemin) - 1):
        cout += graph[chemin[i]][chemin[i+1]]
    return cout

print("\n" + "=" * 60)
print("📝 EXERCICE 4: COMPARAISON DES CHEMINS")
print("=" * 60)

resultats = [
    ("DFS", path_dfs),
    ("BFS", path_bfs),
    ("UCS", path_ucs),
    ("A*", path_astar)
]

# Tableau comparatif détaillé
print("\n📊 TABLEAU COMPARATIF DÉTAILLÉ")
print("=" * 80)
print(f"{'Algorithme':<12} {'Chemin':<35} {'Nb étapes':<12} {'Coût (km)':<10}")
print("-" * 80)

for nom, chemin in resultats:
    if chemin:
        chemin_str = " → ".join(chemin)
        nb_etapes = len(chemin) - 1
        cout = calculer_cout_chemin(chemin, graph_villes_maroc)
        print(f"{nom:<12} {chemin_str:<35} {nb_etapes:<12} {cout:<10}")
    else:
        print(f"{nom:<12} {'Aucun chemin trouvé':<35} {'-':<12} {'-':<10}")

print("-" * 80)

# Analyse comparative
print("\n📈 ANALYSE COMPARATIVE")
print("-" * 60)

# Trouver le chemin optimal
chemins_valides = [(nom, chemin, calculer_cout_chemin(chemin, graph_villes_maroc), len(chemin)-1)
                   for nom, chemin in resultats if chemin]

if chemins_valides:
    # Meilleur par coût
    meilleur_cout = min(chemins_valides, key=lambda x: x[2])
    # Meilleur par nombre d'étapes
    moins_etapes = min(chemins_valides, key=lambda x: x[3])

    print(f"\n🏆 CHEMIN OPTIMAL (coût minimum):")
    print(f"   Algorithme: {meilleur_cout[0]}")
    print(f"   Chemin: {' → '.join(meilleur_cout[1])}")
    print(f"   Coût total: {meilleur_cout[2]} km")
    print(f"   Nombre d'étapes: {meilleur_cout[3]}")

    # Comparaison avec les autres
    print(f"\n📉 COMPARAISON AVEC LES AUTRES ALGORITHMES:")
    for nom, chemin, cout, etapes in chemins_valides:
        if nom != meilleur_cout[0]:
            diff = cout - meilleur_cout[2]
            pourcent = (diff / meilleur_cout[2]) * 100 if meilleur_cout[2] > 0 else 0
            print(f"   {nom}: {cout} km (+{diff} km, +{pourcent:.1f}%)")

# Conclusions
print("\n" + "=" * 60)
print("📝 CONCLUSIONS")
print("=" * 60)

print("""
1. DFS (Depth-First Search):
   - Trouve un chemin rapidement mais PAS optimal
   - Ne garantit pas le chemin le plus court
   - Utile quand on veut juste UNE solution

2. BFS (Breadth-First Search):
   - Trouve le chemin avec le MOINS D'ÉTAPES
   - Optimal seulement si tous les coûts sont égaux
   - Pas optimal pour les distances pondérées

3. UCS (Uniform Cost Search):
   - Trouve le chemin OPTIMAL en termes de coût
   - Explore plus de noeuds que A*
   - Garanti optimal pour tout graphe pondéré

4. A* (A-Star):
   - Trouve le chemin OPTIMAL comme UCS
   - Plus EFFICACE grâce à l'heuristique
   - Explore moins de noeuds que UCS
   - Nécessite une heuristique admissible
""")

# Vérification que A* et UCS trouvent le même résultat
if path_ucs and path_astar:
    cout_ucs = calculer_cout_chemin(path_ucs, graph_villes_maroc)
    cout_astar = calculer_cout_chemin(path_astar, graph_villes_maroc)
    if cout_ucs == cout_astar:
        print("✅ VÉRIFICATION: UCS et A* trouvent le même coût optimal!")
        print(f"   Coût optimal = {cout_ucs} km")
    else:
        print("⚠️  UCS et A* ont des coûts différents!")

# ============================================================
# TEST DE L'AGENT DE RÉSOLUTION
# ============================================================

print("\n" + "=" * 60)
print("🤖 TEST DE L'AGENT DE RÉSOLUTION DE PROBLÈMES")
print("=" * 60)

# Créer l'agent avec UCS (optimal)
agent = ProblemSolvingAgent(
    name="VoitureAutonome",
    search_strategy=SearchStrategy.ucs,
    problem=problem
)

print(f"\n🚗 Agent: {agent.name}")
print(f"📍 Départ: {ETAT_INITIAL} (Rabat)")
print(f"🎯 Destination: {ETAT_BUT} (Marrakech)")
print("\n🚦 Simulation du trajet:")
print("-" * 40)

# Simulation
current_location = ETAT_INITIAL
step = 0
while not agent.done and step < 10:
    percept = NavigationPercept(current_location, problem)
    action = agent.program(percept)
    if action and action.startswith("move_to_"):
        current_location = action.replace("move_to_", "")
    step += 1

print("\n✅ Simulation terminée!")
print("=" * 60)

