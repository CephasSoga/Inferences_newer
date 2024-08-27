from dataclasses import dataclass
from typing import Callable, Dict,  List, Set, Optional, Any


@dataclass
class Refactor:
    args: Set[List[str]]

    def exec(self, *args, **kwargs):
        pass

    def constraint(self, func: Callable[..., Any]) -> Set:
        return set(map(func, self.args))
