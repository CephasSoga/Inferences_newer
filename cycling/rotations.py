from  dataclasses import dataclass
from typing import Set, List, Optional
@dataclass
class Rotator:
    args: Set[List[str]]
    diary: Optional[List] = []
    iteration = 0

    def next(self):
        if len(self.diary) == 0:
            self.iteration += 1
            self.diary.append(self.args[0])
            return self.args[0]
        else:
            _next_value = self.args[self.iteration]
            self.diary.append(_next_value)
            self.iteration += 1
            return _next_value
        
    def previous(self):
        if len(self.diary) == 0:
            return None
        else:
            _previous_iteration = self.iteration - 1
            if _previous_iteration < 0:
                _previous_iteration = len(self.diary) - 1
            return self.diary[_previous_iteration]
        
    def current(self):
        return self.diary[self.iteration]

