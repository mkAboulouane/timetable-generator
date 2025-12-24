from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable,Any,Tuple

from collections import deque
import heapq

import sys

# Ajouter le chemin src au Python path
sys.path.append('../../ch2-agents/src')  # ou './src' selon votre structure
# Importer toutes les classes
from agent  import Agent, Action,Action,Environment,Percept,Sensor

# ----------------------------
# Problem Formulation 
# ----------------------------
class Problem(ABC):
    """
    Classe abstraite représentant un problème de recherche formel
    selon la définition AIMA avec 5 composants
    """
    
    def __init__(self, initial_state: Any, goal: Any = None):
        self.initial_state = initial_state
        self.goal_state = goal
    
    @abstractmethod
    def actions(self, state: Any) -> List[Any]:
        """Retourne les actions possibles depuis un état donné"""
        pass
    
    @abstractmethod
    def result(self, state: Any, action: Any) -> Any:
        """Modèle de transition: état résultant après une action"""
        pass
    
    @abstractmethod
    def goal_test(self, state: Any) -> bool:
        """Test si un état satisfait le but"""
        pass
    
    def path_cost(self, cost_so_far: float, state1: Any, action: Any, state2: Any) -> float:
        """Coût du chemin - souvent additif"""
        return cost_so_far + 1  # Coût uniforme par défaut
# ----------------------------
# Navigation Problem
# ----------------------------   
class NavigationProblem(Problem):
    """Problème de navigation AVEC graphe"""
    
    def __init__(self, initial_state: str, goal: str, graph: dict):
        super().__init__(initial_state, goal)  
        self.graph = graph
    
    def actions(self, state: str) -> List[str]:
        return list(self.graph.get(state, {}).keys())
    
    def result(self, state: str, action: str) -> str:
        return action
    
    def goal_test(self, state: str) -> bool:
        return state == self.goal_state
    
    def path_cost(self, state1: str, action: str, state2: str) -> float:
        return self.graph[state1][action]

    def get_successors(self, state: str) -> List[Tuple[str, float]]:
        return [(action, self.graph[state][action]) for action in self.actions(state)]
    
# ----------------------------
# Search Strategy 
# ----------------------------
class SearchStrategy:
    """Classe unifiée pour toutes les stratégies de recherche"""
    
    @staticmethod
    def dfs(problem):
        return SearchStrategy._search(problem, "dfs")
    
    @staticmethod
    def bfs(problem):
        return SearchStrategy._search(problem, "bfs")
    
    @staticmethod
    def ucs(problem):
        return SearchStrategy._search(problem, "ucs")
    
    @staticmethod
    def a_star(problem, heuristics=None):
        return SearchStrategy._search(problem, "a-star", heuristics)
    
    @staticmethod
    def _search(problem, strategy, heuristics=None):
        """Méthode principale unifiée pour toutes les recherches"""
        
        # Initialisation selon la stratégie
        if strategy in ["dfs", "bfs"]:
            frontiere = deque([problem.initial_state])
        elif strategy == "ucs":
            frontiere = [(0, problem.initial_state)]
        elif strategy == "a-star":
            frontiere = [(heuristics[problem.initial_state], problem.initial_state)]
        
        explore = set()
        parents = {}
        cout_cumule = {problem.initial_state: 0}
        trace = Trace(problem)
        
        iteration = 0
        trace.init_trace(frontiere, explore, strategy)
        
        while frontiere:
            # Sélection de l'état selon la stratégie
            if strategy == "dfs":
                etat_actuel = frontiere.pop()
            elif strategy == "bfs":
                etat_actuel = frontiere.popleft()
            elif strategy == "ucs":
                cout_actuel, etat_actuel = heapq.heappop(frontiere)
                if cout_actuel != cout_cumule[etat_actuel]:
                    continue
            elif strategy == "a-star":
                f_actuel, etat_actuel = heapq.heappop(frontiere)
                g_actuel = cout_cumule[etat_actuel]
                if f_actuel != g_actuel + heuristics[etat_actuel]:
                    continue
            
            # Test du but
            if problem.goal_test(etat_actuel):
                trace.goal_trace(iteration, etat_actuel, frontiere, explore, parents, cout_cumule)
                chemin = trace.chemin_str.split(" -> ")
                return chemin
            
            # Exploration si pas encore exploré
            if etat_actuel not in explore:
                explore.add(etat_actuel)
                
                successeurs = list(problem.get_successors(etat_actuel))
                for successeur, cout in successeurs:
                    nouveau_cout = cout_cumule[etat_actuel] + cout
                    
                    # Condition d'ajout selon la stratégie
                    if strategy in ["dfs", "bfs"]:
                        if successeur not in explore:
                            parents[successeur] = etat_actuel
                            cout_cumule[successeur] = nouveau_cout
                            frontiere.append(successeur)
                    
                    elif strategy == "ucs":
                        if successeur not in cout_cumule or nouveau_cout < cout_cumule[successeur]:
                            cout_cumule[successeur] = nouveau_cout
                            parents[successeur] = etat_actuel
                            heapq.heappush(frontiere, (nouveau_cout, successeur))
                    
                    elif strategy == "a-star":
                        if successeur not in cout_cumule or nouveau_cout < cout_cumule[successeur]:
                            cout_cumule[successeur] = nouveau_cout
                            parents[successeur] = etat_actuel
                            f_successeur = nouveau_cout + heuristics[successeur]
                            heapq.heappush(frontiere, (f_successeur, successeur))
            
            # Trace d'itération
            if strategy in ["ucs", "a-star"]:
                frontiere_triee = sorted(frontiere, key=lambda x: x[0])
                trace.iteration_trace(iteration, etat_actuel, frontiere_triee, explore, parents, cout_cumule)
            else:
                trace.iteration_trace(iteration, etat_actuel, list(frontiere), explore, parents, cout_cumule)
            
            iteration += 1
        
        print("✗ AUCUN CHEMIN TROUVÉ")
        return None
# ----------------------------
# Tracabilite  
# ----------------------------
class Trace:
    def __init__(self, problem):
        self.problem = problem
        self.chemin_str = ""
        self.algo=""
        self.strategies={
            "dfs":"Recherche en profondeur",
            "bfs":"Recherche en largeur",
            "ucs":"Recherche avec cout uniforme",
            "a-star":"Recherche a-star avec heuristique",

        }

    def init_trace(self, frontiere, explore,algo):
        print(f"{60*'='}")
        print(f"  🧾 Traces/log de la {self.strategies.get(algo)}")
        print(f"{60*'='}")
        print(f"\n Initialisation de Frontière 🚧 avec  État initial🚩:")
        print(f"{50*'-'}")
        print(f"🚩 État initial : {self.problem.initial_state}")
        print(f"🚧 Frontière : {list(frontiere)}")
        print(f"📂 Explorés : {list(explore)}")
        print(f"💰 Coût initial : 0\n")
    
    def iteration_trace(self, iteration, etat_actuel, frontiere, explore, parents, cout_cumule):
        print(f"\n🔄 Itération {iteration}:")
        print(f"{50*'-'}")
        print(f"🧩 État actuel : '{etat_actuel}' (coût : {cout_cumule[etat_actuel]})")
        print(f"❓ Test du but : {self.problem.goal_test(etat_actuel)}")
        
        # Nettoyage visuel des doublons
        frontiere_aff = list(dict.fromkeys(list(frontiere)))
        explore_aff = list(dict.fromkeys(list(explore)))
        
        print(f"🚧 Frontière : {frontiere_aff}")
        print(f"📂 Explorés : {explore_aff}")
        
        # Reconstruction du chemin actuel
        chemin_actuel = []
        temp = etat_actuel
        while temp in parents:
            chemin_actuel.append(temp)
            temp = parents[temp]
        chemin_actuel.append(self.problem.initial_state)
        self.chemin_str = ' -> '.join(chemin_actuel[::-1])
        
        print(f"🔗 Chemin : {self.chemin_str}")
        print(f"💰 Coût cumulé : {cout_cumule[etat_actuel]}")
    
    def goal_trace(self, iteration, etat_but, frontiere, explore, parents, cout_cumule):
        self.iteration_trace(iteration, etat_but, frontiere, explore, parents, cout_cumule)
        print(f"\n🏁 ✓ BUT ATTEINT À L'ITÉRATION {iteration}")
        print(f"🎯 État but : '{etat_but}'")
        print(f"🔗 Chemin final : {self.chemin_str}")
        print(f"💰 Coût total : {cout_cumule[etat_but]}")
        print("============================================\n")

       
# ----------------------------
# Problem Solving Agent 
# ----------------------------

# NavigationPercept cohérent
class NavigationPercept(Percept):
    def __init__(self, location: str, problem: Problem):
        self.location = location
        self.problem = problem
    
    @property
    def neighbors(self):
        """Utilise la même méthode que get_successors mais format différent"""
        successors = self.problem.get_successors(self.location)
        return {state: cost for state, cost in successors}
    
    def percept_formulation(self):
        return {"location": self.location, "neighbors": self.neighbors}
    
    def get(self, key: str, default=None):
        """Implémentation correcte de la méthode get"""
        if key == "location":
            return self.location
        elif key == "neighbors":
            return self.neighbors
        else:
            return default  # CORRECTION: retourner default si clé inconnue
    
class ProblemSolvingAgent(Agent):
    """Agent de résolution de problèmes selon l'architecture AIMA"""
    
    def __init__(self, 
                 name: str, 
                 search_strategy: Callable,
                 problem: Any):  # SUPPRIMER goal_function - le but est dans le problème
        super().__init__(name)
        self.search_function = search_strategy
        self.problem = problem  # Le problème contient déjà le but
        
        # État interne de l'agent
        self.seq = deque()  # Séquence d'actions
        self.state = None   # État courant
        self.current_problem = None # Problème courant
        self.done = False   # Indicateur de fin

    def update_state(self, state: Any, percept: Percept) -> Any:
        """Met à jour l'état basé sur la perception"""
        return percept.get("location")

    def formulate_goal(self) -> Any:
        """Récupère le but depuis le problème template"""
        return self.problem.goal_state  # But déjà défini

    def formulate_problem(self, state: Any) -> Any:
        """Formule le problème avec l'état courant mais but fixe"""
        return type(self.problem)(
            initial_state=state, 
            goal=self.problem.goal_state,  # Même but
            graph=self.problem.graph
        )

    def search(self, problem: Any) -> Optional[List[Any]]:
        """Recherche une solution au problème"""
        return self.search_function(problem)

    def program(self, percept: Percept) -> Optional[Action]:
        """Programme principal de l'agent"""
        
        # 1. Mettre à jour l'état interne
        self.state = self.update_state(self.state, percept)
        
        # 2. Si séquence vide, formuler problème et rechercher
        if not self.seq:
            goal = self.formulate_goal()
            
            # Test si déjà au but
            if self.state == goal:
                self.done = True
                print(f"🎯 {self.name}: Déjà au but {goal}!")
                return None
            
            # Formuler et résoudre le problème
            self.current_problem = self.formulate_problem(self.state)
            solution = self.search(self.current_problem)
            
            if solution is None:
                print(f"❌ {self.name}: Aucune solution de {self.state} à {goal}!")
                return None
            
            if len(solution) > 1:
                self.seq = deque(solution[1:])
                print(f"📋 {self.name}: Plan: {' → '.join(solution)}")
            else:
                self.done = True
                return None

        # 3. Exécuter la prochaine action
        if self.seq:
            next_state = self.seq.popleft()
            action = f"move_to_{next_state}"
            
            self.history.append((percept, action))
            self.performance -= 1
            
            print(f"🚗 {self.name}: {self.state} → {next_state}")
            self.state = next_state
            return action

        return None