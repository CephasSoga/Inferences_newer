from pathlib import Path
from typing import Union, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Insight:
    labels: List[str] = []
    tags: List[str] = []


    def __call__(self):
        return {
            'labels': self.labels,
            'tags': self.tags
        }