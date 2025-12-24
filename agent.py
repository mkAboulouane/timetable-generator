from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

# Types de base
Percept = Dict
Action = str


# ----------------------------
# Agent abstrait
# ----------------------------
class Agent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.history: List[Tuple[Percept, Action]] = []
        self.performance = 0.0
    
    @abstractmethod
    def program(self, percept: Percept) -> Optional[Action]:
        """Programme de l'agent - décide de l'action basée sur le percept"""
        pass
    
    def get_performance(self) -> float:
        """Retourne la performance courante de l'agent"""
        return self.performance
# ----------------------------
# Environnement abstrait
# ----------------------------
class Environment(ABC):
    def __init__(self):
        self.agents = []
    
    @abstractmethod
    def get_percepts(self, agent: Agent) -> Percept:
        """Retourne les percepts pour un agent donné"""
        pass
    
    @abstractmethod
    def apply_action(self, agent: Agent, action: Action) -> None:
        """Applique l'action d'un agent à l'environnement"""
        pass
    
    def step(self) -> None:
        """Exécute un pas de simulation pour tous les agents"""
        for agent in self.agents:
            percept = self.get_percepts(agent)
            action = agent.program(percept)
            if action is not None:
                self.apply_action(agent, action)
    
    def run(self, steps: int = 100) -> None:
        """Exécute la simulation pour un nombre donné d'étapes"""
        for _ in range(steps):
            if self.is_done():
                break
            self.step()
    
    def is_done(self) -> bool:
        """Détermine si la simulation est terminée"""
        return False



# ----------------------------
# Capteur abstrait
# ----------------------------
class Sensor(ABC):
    @abstractmethod
    def sense(self, env: Environment, agent: Agent) -> Percept:
        """Capture les informations de l'environnement pour l'agent"""
        pass

# ----------------------------
# Actionneur abstrait
# ----------------------------
class Actuator(ABC):
    @abstractmethod
    def act(self, env: Environment, agent: Agent, action: Action) -> None:
        """Exécute l'action dans l'environnement"""
        pass
