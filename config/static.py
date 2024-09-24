from enum import Enum

class BroadConfigArgs(Enum):
    SUMMARY_ARGS = {
        "model_name": "gpt-4o",
        "tokens_max_count": 16
    }

    PROMPT_EDGES = {
        "opening": ("You are trying to predict future outcomes of related events." 
            "You are given only one event at a time but they are provided in sequence.\n" 
            "Those events are called stages. A stage deescribe the current state of the world."
            "You may have produced a one or more predictions already for other events (stages);"
            "if so, build the next one on top of them."
            "When provided in sequence, events (stages) build the context you should use for the next prediction.\n"
            "You will find all previous stages and their corresponding predictions in the history (included in this prompt).\n"
            "All the information the context carries has been carefully selectedm reviewed and analyzed by YOU in an automated process.\n"
            "The following statement is called a partial stage statement or a query, for short. It is the content of the current stage.\n"
            "Query: "),

        "closing": ("\nNow that you had a look at the query, try to predict what outcomes are the most likely."
            #"Be detailed and explain your predictions." 
            "Include details you find interessing to enrich your predictions." 
            "Use formal writing style, as if you are writing a financial news article."
            "Keep it literal and concise. The writing style should be as clear as possible. IT IS IMPORTANT\n")
    }

    IMAGE_SIZE = "512x512"

class InferencesArgs(Enum):
    MODEL_NAME = "gpt-4o"
    REQUETS_TYPE = "everything"
    QUERIES = ["apple stocks", "market performance"]
    MONGODB_URI = mongodb_uri = "mongodb+srv://nukunucephassoga:kq61oh2eqEp6kCVj@cluster0.pfwp8bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

class RequestsArgs(Enum):
    CATEGORIES = ["business", "general", "technology"]
    COUNTRIES = ["us"]
    QUERIES = [['stocks', 'market performance'], ['crypto', 'bitcoin', 'ethereum', 'cardano', 'dogecoin'], ['apple', 'microsoft']]
    PAGE_SIZE = 100
    SIZE = 100

class Balancer:
    STOP_COUNT: int = 3