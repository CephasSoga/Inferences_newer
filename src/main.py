# Copyright 2024 Cube AI, Inc.
# **All Rights Reserved**
# @author: Cephas Nukunu Soga
# @email: sogacephas@gmail.com
# @github: https://github.com/cephassoga
# @date: 2024-08-31
# @company: Cube AI, Inc.

import os
import asyncio
from worker.predictor import MainWorker


if __name__ == "__main__":
    # raises exceptions sometimes during api calls
    # such exceptions are handled
    # by a retry mechanism directrly in the main worker
    # but failure can still occur even with the retry decorator being used to actively handle it
    # that is beacuse some tokens (words/terms) in the inference base may trigger OpenAi's restriction policy
    # and thus may not be able to be processed
    # this will make the inference fail and raise an error which will be shut by the excpetion handling logic
    # **NOTE**: logs output will be sent to the console and to a log file
    # **NOTE**: refer to logging for more details
    # **NOTE**: some other error causes may arise as well: http 429 rate limit error, etc\
    # **NOTE**: this code has not been tested aginst those errors but logs still offer an exhaustive error message

    # **NOTE**: storing genreated image urls in the db leads to images being lost after some time.
    # **NOTE**: eventually, storing them as raw bytes (the current approach, which is more efficient in terms of time when retreiving them) 
    # solves it; but is not much efficient in terms of storage.
    asyncio.run(MainWorker().exec())