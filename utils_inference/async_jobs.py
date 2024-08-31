import aiohttp

async def get_bytes(target: str, params: dict = None, headers: dict = None, logger = None) -> bytes | None:
    """Makes an asynchronous HTTP GET request to the News API with the provided parameters and returns the bytes response."""
    if logger is not None:
        logger.log('info' ,f"Requesting URL: {target} with params: {params} and headers: {headers}")
    try:
        async with aiohttp.ClientSession() as session:
                    async with session.get(target, params=params, headers=headers) as response:
                        response.raise_for_status()
                        #render bytes
                        if logger:
                            logger.log('info', 'Request Successful')
                        return await response.content.read()
    except aiohttp.ClientError as e:
        if logger:
            logger.log('info', f"An error occurred while fetching data with params <{params}>", e)
        return None
    