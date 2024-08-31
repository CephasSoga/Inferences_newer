
from newsapi import NewsApiClient

# Init
newsapi = NewsApiClient(api_key='')

# /v2/top-headlines
top_headlines = newsapi.get_top_headlines(q='apple',
                                          #sources='bbc-news,the-verge',
                                          category='business',
                                          language='en',
                                          country='us')

# /v2/everything
'''all_articles = newsapi.get_everything(q='bitcoin',
                                      sources='bbc-news,the-verge',
                                      domains='bbc.co.uk,techcrunch.com',
                                      from_param='2024-08-28',
                                      to='2024-08-29',
                                      language='en',
                                      sort_by='relevancy',
                                      page=1)

# /v2/top-headlines/sources
sources = newsapi.get_sources()'''

print("Result: ", top_headlines)