from typing import List

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import pos_tag

from janine.RichText import TextCompletion

class Processor:

    def minimize(self, text: str) -> str:
        """Remove stop words and non-alphabetic tokens from the text."""
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text)
        min_qx = [word for word in words if word.isalpha() and word.lower() not in stop_words]
        return " ".join(min_qx)
    
    def extract_kwds(self, text: str) -> List[str]:
        """Extract nouns from the text."""
        words = word_tokenize(text)
        tagged_words = pos_tag(words)
        return [word for word, pos in tagged_words if pos.startswith('NN')]
    
    async def make_summary(self, text: str, tokens_max_count: int = 48, model_name: str = "gpt-3.5-turbo"):
        if not text or not tokens_max_count:
            return ""
        completion_model = TextCompletion()
        completion_model.model = model_name
        completion_model.context = f"You analyze texts and provide summaries up to {tokens_max_count} tokens"
        completion_model.instruction = "Generate a summary for the provided text."
        summary = await completion_model.textCompletion(textInput=text)

        return summary
        