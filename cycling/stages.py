import inspect
from typing import List, Callable, Optional, Any
from dataclasses import dataclass
from functools import partial


@dataclass
class Stage:
    name: str
    description: str
    query: str

class Traverser:
    def __init__(self, stages: List[Stage]):
        self.stages = stages
        self.final_result: str = None

        self.results = []

    async def result(self, stage: Stage, func: Callable[[Stage, Optional[dict]], Any], **options) -> Any :
        stage_result_func = partial(func, stage)
        if inspect.iscoroutinefunction(func):
            stage_result = await stage_result_func(**options)
        else:
            stage_result = stage_result_func(**options)
        
        return stage_result

    async def traverse(self, func: Callable[[Stage, Optional[dict]], Any], **options) -> List[Any]:
        for index, stage in enumerate(self.stages):
            stage_result = await self.result(stage, func, **options)
            self.results.append(stage_result)
            if index < len(self.stages) - 1:
                self.final_result = stage_result
                break

        return self.final_result
        
   