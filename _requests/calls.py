import aiohttp
import json
from typing import List
from dataclasses import dataclass
from datetime import datetime

from utils_inference.logs import Logger


# simple interface - not meant to be used directly: The request to the news API will match this pattern or `None` if the request was not successful.
resultPattern = {
    "status": "ok",
    "totalResults": 0,
    "articles": []
}

@dataclass
class Article:
    """Interface of an Article object."""
    title: str
    author: str
    url: str
    description: str
    urlToImage: str
    publishedAt: str
    content: str

    def __repr__(self) -> str:
        return json.dumps({
            'title': self.title,
            'author': self.author,
            'url': self.url,
            'description': self.description,
            'urlToImage': self.urlToImage,
            'publishedAt': self.publishedAt,
            'content': self.content
        }, indent=4)
    
    def __str__(self) -> str:
        return self.__repr__()


class NewsRequest:
    """Class for making requests to the news API."""
    def __init__(self):
        """Initializes the class with a logger, API key, base URL, and an aiohttp ClientSession."""
        self.logger = Logger("Headlines-Request")
        self.apikey = "b11bb9f5fb68447397ee4a270fecb49d"
        self.base_url = "https://newsapi.org/v2/top-headlines"

        self.client = aiohttp.ClientSession()

    async def request(self, url: str,   q: str | list[str] = None, country: str = None, search_in: str = None, domains: str = None, from_param: datetime | str = None, to: datetime |str = None, category: str = None, sources: str = None, language: str = "en", pageSize: int = None, page: int = None, sortBy: str = None) -> dict:
        """Makes an asynchronous HTTP GET request to the News API with the provided parameters and returns the JSON response."""
        if (search_in and not q):
            raise ValueError("if you provide `search_in`, you must also provide `q`.")
        
        if search_in not in [None, 'title', 'description', 'content']:
            raise ValueError("Invalid `search_in` argument. Choose from [None, 'title', 'description', 'content']")
        
        if not sortBy in [None, 'relevancy', 'publishedAt', 'popularity']:
            raise ValueError("Invalid `sortBy` argument. Choose from [None, 'relevancy', 'publishedAt', 'popularity']")
        
        if pageSize and pageSize > 100:
            raise ValueError("Invalid `pageSize` argument. Choose a number between 1 and 100")
        
        if page and page < 1:
            raise ValueError("Invalid `page` argument. Choose a number greater than 0")
        
        params = {}

        params['apiKey'] = self.apikey

        if q:
            params['q'] = q
        if country:
            params['country'] = country
        if category:
            params['category'] = category
        if sources:
            params['sources'] = sources
        if language:
            params['language'] = language
        if pageSize:
            params['pageSize'] = pageSize
        if page:
            params['page'] = page
        if sortBy:
            params['sortBy'] = sortBy
        if from_param:
            params['from'] = from_param
        if to:
            params['to'] = to
        if domains:
            params['domains'] = domains
        if search_in:
            params['searchIn'] = search_in

        async with self.client.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Error: {response.status} - {await response.text()}")
            else:
                return await response.json()

    async def headlines(self, q: str | list[str] = None, country: str = None, category: str = None, sources: str = None, language: str = "en", pageSize: int = None, page: int = None, sortBy: str="relevancy") -> dict:
        """Calls the request method to fetch top headlines based on the provided parameters."""
        url = 'https://newsapi.org/v2/top-headlines'
        self.logger.log("info", f"Requesting  news headlines from {url} with params: {locals()}")
        try:
            return await self.request(
                url=url, 
                q=q, 
                country=country, 
                category=category, 
                sources=sources, 
                language=language, 
                pageSize=pageSize, 
                page=page, 
                sortBy=sortBy
            )
        except Exception as e:
            self.logger.log("error", "Error encountered while requesting news headlines", e)
            
    async def everything(self, q: str | list[str] = None, sources: str = None, search_in: str = None, domains: str = None, from_param: str = None, to: str = None, language: str = "en", page:  int = None, pageSize: int = None, sortBy: str="relevancy") -> dict:
        """Calls the request method to fetch news articles based on the provided parameters."""
        url = 'https://newsapi.org/v2/everything'
        self.logger.log("info", f"Requesting  news articles from{url} with params: {locals()}")
        try:
            return await self.request(
                url=url, 
                q=q, 
                sources=sources, 
                search_in=search_in, 
                domains=domains, 
                from_param=from_param, 
                to=to, 
                language=language,
                page=page,
                pageSize=pageSize, 
                sortBy=sortBy
            )
        except Exception as e:
            self.logger.log("error", "Error encountered while requesting news articles", e)
    
    async def  close(self):
        """Closes the aiohttp ClientSession."""
        await self.client.close()

@dataclass
class Parser:
    """Handles the parsing of the JSON response from the News API into a list of Article objects."""
    arg: dict

    def __call__(self):
        """Parses the JSON response and yields Article objects."""
        target = self.arg['articles']
        for article in target:
            yield Article(
                title=article['title'],
                author=article['author'],
                url=article['url'],
                description=article['description'],
                urlToImage=article['urlToImage'],
                publishedAt=article['publishedAt'],
                content=article['content'],
            )

async def main():
    import time
    s = time.perf_counter()
    request = NewsRequest()
    r = await request.everything(q="apple stocks", from_param='2024-08-28')
    print("Result: ", r['totalResults'])
    p = Parser(r)
    #for article in p():
    #    print(article)
    await request.close()
    e = time.perf_counter()
    print(f"Finished in {e-s:0.4f} seconds")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

