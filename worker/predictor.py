import json
import uuid
import time
import random
import inspect
import asyncio
import concurrent.futures as futures
from typing import List, Callable, Optional, Any, Dict
from dataclasses import dataclass
from functools import partial, wraps
from datetime import datetime


from janine.RichText import TextCompletion
from janine.Generators import ImageGenerator
from utils_inference.logs import Logger, async_timer, timer
from utils_inference.async_jobs import get_bytes
from _requests.calls import NewsRequest, Parser
from config.static import BroadConfigArgs, Balancer, InferencesArgs
from worker.processor import Processor
from worker.db_handler import MongoPusher, ImageBinary

MAX_RETRIES = 3
DELAY_AFTER_FAILURE = 1
BACKOFF_FACTOR = 2

def retry(max_attempts=MAX_RETRIES, delay=DELAY_AFTER_FAILURE, backoff=BACKOFF_FACTOR):
    delay = delay
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Function {func.__name__} on attempt {attempts}/{max_attempts} failed with error: {e}")
                    attempts += 1
                    delay *= backoff
                    if attempts < max_attempts:
                        print(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        raise e
        return wrapper
    return decorator


def async_retry(max_attempts=MAX_RETRIES, delay=DELAY_AFTER_FAILURE, backoff=BACKOFF_FACTOR):
    delay = delay
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    if inspect.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Async function {func.__name__} on attempt {attempts}/{max_attempts} failed with error: {e}")
                    attempts += 1
                    delay *= backoff
                    if attempts < max_attempts:
                        print(f"Retrying in {delay} seconds...")
                        asyncio.sleep(delay)
                    else:
                        raise e
        return wrapper
    return decorator

@dataclass
class Stage:
    name: str
    description: str
    query: str
    labels: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    def __post_init__(self):
        opening = BroadConfigArgs.PROMPT_EDGES.value["opening"]
        closing = BroadConfigArgs.PROMPT_EDGES.value["closing"]
        self.query = opening + self.query + closing

@dataclass
class Inference:
    title: str
    description: str
    content: str
    date: str
    image: Optional[bytes]
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
            'image': "bytes" if self.image else "None",
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
            'image': self.image,
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
        self.completion_agent.model = InferencesArgs.MODEL_NAME.value

        self.history: List[Dict[str, Any]] = [] # an updatable history attribute

        self.logger = Logger("Inference-Worker")

    async def result(self, stage: Stage, func: Callable[[Stage, Optional[dict]], Any], **options) -> Any :
        stage_result_func = partial(func, stage) # partially freeze the function
        if inspect.iscoroutinefunction(func):
            stage_result = await stage_result_func(**options) 
        else:
            stage_result = stage_result_func(**options)
        
        return stage_result
    
    @async_retry()
    @async_timer()
    async def process_stage(self, stage: Stage, history: List[Dict[str, Any]], **options) -> str | None:
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

    async def single_inference_base(self, q, type: str = 'headlines', stop_count: int = ... , **options) -> List[Stage]:
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
        
    async def inference_base(self, qx: List[str] | List[List[str]], type: str = 'headlines', stop_count: int = ..., **options) -> List[List[Stage]]:
        results = []
        for q in qx:
            result = await self.single_inference_base(q=q, type=type, stop_count=stop_count, **options)
            results.append(result)
        return results

    async def build_base(self, qx: List[str] | List[List[str]] , type: str = 'headlines', stop_count: int = ..., **options):
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
    

    async def make_title(self, text: str, tokens_max_count: int, model_name: str) -> str:
        return await self.processor.make_summary(text, tokens_max_count, model_name)
    
    def make_tags(self, text: str) -> List[str]:
        # TODO: make this more intelligent
        return ["finance", "stock market", "economy"]
    
    async def make_image(self, text: str, image_size: str) -> bytes:
        if not text or len(text) == 0:
            return None
        image_url: List[str | None] = await self.image_model.generate(prompt=text, size=image_size)

        image_bytes = await get_bytes(image_url[0])

        if not image_bytes:
            return None
        
        image_data = ImageBinary.encode_from_bytes(image_bytes)

        return image_data
    
    def precompute_labels(self, texts: List[str]) -> List[List[str]]:
        precomputed_labels = {}
        for idx, text in enumerate(texts):
            precomputed_labels[str(idx)] = self.make_labels(text)
        return precomputed_labels
    
    async def __call__(self, texts: List[str] = None):
        """
        Processes a list of texts and yields Inference objects for each text.

        If no texts are provided, the executor_results attribute of this object is used.

        :param texts: List of texts to process
        :yield: Inference objects
        """

        if not texts and self.executor_results:
            texts = self.executor_results
        precomputed_labels = self.precompute_labels(texts)
        results = {}
        for idx, text in enumerate(texts):
            self.logger.log("info", f"Processing text  at index: {idx + 1} of {len(texts)}")
            title = await self.make_title(text, **BroadConfigArgs.SUMMARY_ARGS.value)
            image = await self.make_image(title, BroadConfigArgs.IMAGE_SIZE.value)
            tags = self.make_tags(text)
            results[str(idx)] = {
                "title": title,
                "description": "Warning: This content is AI generated.",
                "labels": precomputed_labels[str(idx)],
                "tags": tags,
                "urls": [], # TODO: add urls
                "image": image,
                "content": text
            }
        for key in results.keys():
            yield Inference(
                date=datetime.now().date().isoformat(),
                title=results[key]["title"],
                description=results[key]["description"],
                content=results[key]["content"],
                image=results[key]["image"],
                urls=results[key]["urls"],
                labels=results[key]["labels"],
                tags=results[key]["tags"]
            )
            self.logger.log("info", f"Finished processing text at index: {idx + 1} of {len(texts)}")


class MainWorker:
    logger = Logger("Main-Worker")
    inferences = set()
    async def exec(
            self, db_uri: str = InferencesArgs.MONGODB_URI.value, 
            qx: str | List[str] = InferencesArgs.QUERIES.value, 
            type: str = InferencesArgs.REQUETS_TYPE.value, 
            stop_count: int = Balancer.STOP_COUNT,
            **options):
        try:
            executor = Executor()
            await executor.build_base(qx=qx, type=type, stop_count=stop_count, **options)
            results = executor(executor.stage_wrapper[:stop_count])
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
            try:
                _ = pusher.remove_outdated()
            except Exception as e:
                self.logger.log("error", "An error occurred while removing outdated collections", e)
            finally:
                pusher.close()







