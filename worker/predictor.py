import inspect
from typing import List, Callable, Optional, Any, Dict
from dataclasses import dataclass
from functools import partial


from janine.RichText import TextCompletion
from cycling.stages import Traverser, Stage
from utils_inference.logs import Logger


@dataclass
class Stage:
    name: str
    description: str
    query: str
    labels: Optional[List[str]] = None
    tags: Optional[List[str]] = None



class Worker:
    """
    Worker class for processing stages and performing text completion.

    Attributes:
        stages: List of Stage objects representing the stages to be processed.
        model: TextCompletion object for performing text completion.
        history: List of dictionaries representing the conversation history.

    Methods:
        result: Asynchronously executes a function with a frozen stage and options.
        process_stage: Asynchronously processes a stage by performing text completion and updating the history.
        exhaust_stages: Asynchronously processes all stages in the worker's stages list.
    """
    def __init__(self, stages: List[Stage]):
        self.stages = stages
        self.completion_agent = TextCompletion()
        self.completion_agent.model = "gpt-3.5-turbo"

        self.history: List[Dict[str, Any]] = [] # an updatable history attribute

        self.logger = Logger("Inference-Worker")

    async def result(self, stage: Stage, func: Callable[[Stage, Optional[dict]], Any], **options) -> Any :
        
        """
        Asynchronously executes a function with a frozen stage and options.

        Args:
            stage (Stage): The stage to be processed.
            func (Callable[[Stage, Optional[dict]], Any]): The function to be executed.
            **options: Additional keyword arguments passed to the function.

        Returns:
            Any: The result of the function execution.
        """
        stage_result_func = partial(func, stage) # partially freeze the function
        if inspect.iscoroutinefunction(func):
            stage_result = await stage_result_func(**options) 
        else:
            stage_result = stage_result_func(**options)
        
        return stage_result
    

    async def process_stage(self, stage: Stage, history: List[Dict[str, Any]], **options) -> str | None:
        """
        Asynchronously processes a stage by performing text completion and updating the history.

        Args:
            stage (Stage): The stage to be processed.
            history (List[Dict[str, Any]]): The current conversation history.
            **options: Additional keyword arguments passed to the completion function.

        Returns:
            str | None: The result of the text completion, or None if an error occurred.
        """
        self.logger.log("info", f"Processing stage: {stage.name}")
        query = stage.query

        if not query:
            return None
        
        try:
            stage_result = await self.completion_agent.textCompletion(history=history, textInput=query, **options) # perform completion
        except Exception:
            self.logger.log("error", f"Error processing stage: {stage.name}")
            return None

        records = [{"role": "user","content": query,}, {"role": "system","content": stage_result}] # create the expected record format

        self.history.extend(records) # update history

        self.logger.log("info", f"Stage {stage.name} completed")
        return stage_result
    
    async def exhaust_stages(self):
        """
        Asynchronously processes all stages in the worker's stages list.

        Returns:
            str | None: The result of the last stage's text completion, or None if an error occurred.
        """
        
        for index, stage in enumerate(self.stages):
            stage_result = await self.result(stage, self.process_stage, history=self.history)

            if index == len(self.stages) - 1:
                return stage_result
            

async def main():
    import os
    os.environ["OPENAI_API_KEY"] = "sk-proj-QyWSLHFDxXFRXNiUuTFtT3BlbkFJJiA8SyBqwjGX4TsZGKXj"
    stages = [
        Stage(name="Example Stage", description="This is an example stage", query="hello"),
        Stage(name="Another Example Stage", description="This is another example stage", query="when is chrismas?"),
        Stage(name="Final Stage", description="This is the final stage", query="can it be moved?")
    ]

    worker = Worker(stages)

    r = await worker.exhaust_stages()
    print("history:", worker.history)
    print("Result:", r)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

        