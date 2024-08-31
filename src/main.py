import os
import asyncio
from worker.predictor import MainWorker


if __name__ == "__main__":
    # raises exceptions sometimes during api calls
    # such exceptions are handled
    # by a retry mechanism directrly ion the main worker
    # but failure can still occur even with the retry decorator being used to actively handle it
    # that is beacuse some tokens (words/terms) in the inference base may trigger OpenAi's restriction policy
    # and thus may not be able to be processed
    # this will make the inference fail and raise an erro which will be shut by the excpetion hnadling logic
    # **NOTE**: logs output will be sent to the console and to a log file
    # **NOTE**: refer to logging for more details
    # **NOTE**: some other error causes may arise as well: http 429 rate limit error, etc\
    # **NOTE**: this code has not been tested aginst those errors but logs still offer an exhaustive error message
    asyncio.run(MainWorker().exec())