import json
import uuid
import random
import inspect
import asyncio
import concurrent.futures as futures
from typing import List, Callable, Optional, Any, Dict
from dataclasses import dataclass
from functools import partial
from datetime import datetime


from janine.RichText import TextCompletion
from janine.Generators import ImageGenerator
from cycling.stages import Stage
from utils_inference.logs import Logger
from _requests.calls import NewsRequest, Parser
from _requests.static import queries, mongodb_uri
from worker.processor import Processor
from worker.db_handler import MongoPusher


@dataclass
class Stage:
    name: str
    description: str
    query: str
    labels: Optional[List[str]] = None
    tags: Optional[List[str]] = None

@dataclass
class Inference:
    title: str
    description: str
    content: str
    date: str
    image_url: Optional[str]
    urls: Optional[List[str]]
    labels: Optional[List[str]]
    tags: Optional[List[str]]

    def __post_init__(self):
        self.id = str(uuid.uuid4()) + "".join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))

    def __repr__(self):
        return json.dumps({
            'title': self.title,
            'date': self.date,
            'id': self.id,
            'description': self.description,
            'content': self.content,
            'image_url': self.image_url,
            'urls': self.urls,
            'labels': self.labels,
            'tags': self.tags
        }, indent=4)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'date': self.date,
            'image_url': self.image_url,
            'urls': self.urls,
            'labels': self.labels,
            'tags': self.tags
        }
    
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Inference):
            return self.id == other.id
        return False


class Worker:
    def __init__(self, stages: List[Stage]):
        self.stages = stages
        self.completion_agent = TextCompletion()
        self.completion_agent.model = "gpt-3.5-turbo"

        self.history: List[Dict[str, Any]] = [] # an updatable history attribute

        self.logger = Logger("Inference-Worker")

    async def result(self, stage: Stage, func: Callable[[Stage, Optional[dict]], Any], **options) -> Any :
        stage_result_func = partial(func, stage) # partially freeze the function
        if inspect.iscoroutinefunction(func):
            stage_result = await stage_result_func(**options) 
        else:
            stage_result = stage_result_func(**options)
        
        return stage_result
    

    async def process_stage(self, stage: Stage, history: List[Dict[str, Any]], **options) -> str | None:
        self.logger.log("info", f"Processing stage: [{stage.name}]")
        if not isinstance(stage.name, str) or len(stage.name.strip()) == 0:
            self.logger.log("error", f"Invalid stage name: {stage.name}. Skipping...")
            return None
        query = stage.query

        if not query or len(query.strip()) == 0:
            return None
        
        try:
            stage_result = await self.completion_agent.textCompletion(history=history, textInput=query, **options) # perform completion
        except Exception:
            self.logger.log("error", f"Error processing stage: [{stage.name}]")
            return None
        records = [{"role": "user","content": query,}, {"role": "system","content": stage_result}] # create the expected record format
        self.history.extend(records) # update history

        self.logger.log("info", f"Stage [{stage.name}] completed")

        return stage_result
    
    async def exhaust_stages(self):
        for index, stage in enumerate(self.stages):
            stage_result = await self.result(stage, self.process_stage, history=self.history)

            if index == len(self.stages) - 1:
                return stage_result


class Executor:
    def __init__(self):
        self.request_handler = NewsRequest()
        self.logger = Logger("Inference-Executor")

    async def single_inference_base(self, q, type: str = 'headlines', stop_count: int = 3, **options) -> List[Stage]:
        stages = []
        try:
            if type == 'headlines':
                news = await self.request_handler.headlines(q=q, **options)
            elif type == 'everything':
                news = await self.request_handler.everything(q=q, **options)
            parser = Parser(news)
            articles = parser()
            for article in articles:
                stages.append(
                    Stage(
                        name = article.title,
                        description=article.description,
                        query=article.content or article.title,
                        labels=[], # maybe add something here later
                        tags=[]
                    )
                )
        except Exception as e:
            self.logger.log("error", "Error encountered while requesting news headlines", e)
            return []

        return stages[:stop_count]
        
    async def inference_base(self, qx: List[str] | List[List[str]], type: str = 'headlines', stop_count: int = 3, **options) -> List[List[Stage]]:
        results = []
        for q in qx:
            result = await self.single_inference_base(q=q, type=type, stop_count=stop_count, **options)
            results.append(result)
        return results

    async def build_base(self, qx: List[str] | List[List[str]] , type: str = 'headlines', stop_count: int = 3, **options):
        if not getattr(self, 'stages_wrapper', None):
            self.stage_wrapper = await self.inference_base(qx=qx, type=type, stop_count=stop_count, **options)

    def sync_task_func(self, async_func: Callable):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(async_func())
        return result

    def __call__(self, stages_wrappers: List[List[Stage]] = None):
        if not stages_wrappers:
            if getattr(self, 'stage_wrapper', None):
                stages_wrappers = self.stage_wrapper
            else:
                raise ValueError("No stages wrapper was provided.  Build stages first with `build_stages` method.")
        tasks = []
        with futures.ThreadPoolExecutor(max_workers=len(stages_wrappers)) as executor:
            for stages in stages_wrappers:
                if not stages or len(stages) == 0:
                    return None
                worker = Worker(stages)
                tasks.append(executor.submit(self.sync_task_func, worker.exhaust_stages))
        return [task.result() for task in tasks]

@dataclass
class InferentialWorker:
    executor_results: Any

    def __post_init__(self):
        self.image_model: ImageGenerator = ImageGenerator()
        self.processor: Processor = Processor()

        self.logger: Logger = Logger("Inferential-Worker")

    def make_labels(self, text: str) -> List[str]:
        min_text = self.processor.minimize(text)
        return self.processor.extract_kwds(min_text)
    

    async def make_title(self, text: str, tokens_max_count: int = 48):
        return await self.processor.make_summary(text, tokens_max_count)
    
    def make_tags(self, text: str) -> List[str]:
        # TODO: make this more intelligent
        return ["finance", "stock market", "economy"]
    
    async def make_image(self, text: str) -> str:
        if not text or len(text) == 0:
            return ""
        return await self.image_model.generate(prompt=text)
    
    def precompute_labels(self, texts: List[str]) -> List[List[str]]:
        precomputed_labels = {}
        for idx, text in enumerate(texts):
            precomputed_labels[str(idx)] = self.make_labels(text)
        return precomputed_labels
    
    async def __call__(self, texts: List[str] = None):
        if not texts and self.executor_results:
            texts = self.executor_results
        precomputed_labels = self.precompute_labels(texts)
        results = {}
        for idx, text in enumerate(texts):
            self.logger.log("info", f"Processing text  at index: {idx + 1} of {len(texts)}")
            title = await self.make_title(text)
            image_url = await self.make_image(title)
            tags = self.make_tags(text)
            results[str(idx)] = {
                "title": title,
                "description": "",
                "labels": precomputed_labels[str(idx)],
                "tags": tags,
                "urls": [], # TODO: add urls
                "image_url": image_url,
                "content": text
            }
        for key in results.keys():
            yield Inference(
                date=datetime.now().date().isoformat(),
                title=results[key]["title"],
                description=results[key]["description"],
                content=results[key]["content"],
                image_url=results[key]["image_url"],
                urls=results[key]["urls"],
                labels=results[key]["labels"],
                tags=results[key]["tags"]
            )
            self.logger.log("info", f"Finished processing text at index: {idx + 1} of {len(texts)}")


class MainWorker:
    logger = Logger("Main-Worker")
    inferences = set()
    async def exec(self, db_uri: str = mongodb_uri, qx: str | List[str] = ["apple stocks", "market performance"], type: str = 'everything', stop_count: int = 2, **options):
        try:
            executor = Executor()
            await executor.build_base(qx=qx, type=type, stop_count=stop_count, **options)
            results = executor(executor.stage_wrapper[:2])
            inference_worker = InferentialWorker(results)
            async for result in inference_worker():
                self.inferences.add(result)

            pusher = MongoPusher(None)
            _ = pusher.connect(uri=db_uri)
            result = pusher.bulk_push(self.inferences)
            return result
        except Exception as e:
            self.logger.log("error", "An error occurred while executing the main worker", e)
            raise
        finally:
            await executor.request_handler.close()


if __name__ == "__main__":
    import os
    os.environ["OPENAI_API_KEY"] = "sk-proj-QyWSLHFDxXFRXNiUuTFtT3BlbkFJJiA8SyBqwjGX4TsZGKXj"
    # raises exceptions sometimes during api calls
    # raises exceptions  [Operator '>' not supported for operand types 'str' and 'int'] when pushing
    asyncio.run(MainWorker().exec())





