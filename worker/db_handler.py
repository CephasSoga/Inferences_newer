from typing import List, Set, Any
from dataclasses import dataclass
from datetime import datetime
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from utils_inference.logs import Logger

@dataclass
class MongoPusher:
    def __init__(self, client: MongoClient | None = None) -> None:
        self.client = client
        self.logger = Logger("MongoPusher")

    def connect(self, uri: str | None = None):
        """
        Connects to a MongoDB instance using the provided URI, or the current client if the URI is None.

        Args:
            uri (str | None): The URI to connect to, or None to use the current client.

        Returns:
            bool: Whether the connection was successful.

        Raises:
            ValueError: If no MongoDB URI is provided, and no client is currently connected.
        """
        if uri is None and self.client is None:
            raise ValueError("No MongoDB URI provided")
        self.client = self.client or MongoClient(uri, server_api=ServerApi('1'))
        # send ping to confirm connection
        try:
            self.client.admin.command('ping')
            self.logger.log("info", "Successfully connected to MongoDB")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.log("error", "Failed to connect to MongoDB", e)
            self.client = None
            return False

    def bulk_push(self, data: List[Any] | Set[Any]):
        """
        Push a list or set of inferences to the MongoDB collection, one document per inference.

        :param data: List or set of inferences to push
        :return: True if all inferences were successfully pushed, False otherwise
        :raises ValueError: If no MongoDB client is provided, or if no data is provided to push
        """
        if self.client is None:
            raise ValueError("No MongoDB client provided")
        
        if data is None or len(data) == 0:
            raise ValueError("No data provided to push")
        
        if isinstance(data, Set):
            data = list(data)

        try:
            data = [inference.to_dict() for inference in data]
        except AttributeError:
            data = data

        collection_date = datetime.now().date().isoformat()
        db = self.client['insights']
        collection = db[collection_date]

        self.logger.log("info", f"Bulk Pushing {len(data)} documents to MongoDB collection: {collection_date}")
        try:
            result = collection.insert_many(data)
            self.logger.log("info", f"Successfully pushed {len(result.inserted_ids)} documents to MongoDB collection: {collection_date}")
            return len(result.inserted_ids) > 0        
        except Exception as e:
            self.logger.log("error", f"Error encountered while pushing documents to MongoDB collection: {collection_date}", e)
            return False
        