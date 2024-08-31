import bson
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
        
    def remove_outdated(self):
        """
        Removes all collections from the MongoDB database that are older than 30 days.

        :return: True if any collections were removed, False otherwise
        """
        db = self.client['insights']
        collection_names = db.list_collection_names()
        any_removed = False
        total_collections = len(collection_names)
        removed_collections = 0

        for collection_name in collection_names:
            try:
                collection_date = datetime.strptime(collection_name, "%Y-%m-%d").date()
                if (datetime.now().date() - collection_date).days > 30:
                    self.logger.log("info", f"Removing outdated collection: {collection_name}")
                    db[collection_name].drop()
                    self.logger.log("info", f"Successfully removed outdated collection: {collection_name}")
                    removed_collections += 1
                    any_removed = True
            except Exception as e:
                self.logger.log("error", f"Error encountered while removing outdated collection: {collection_name}", e)

        self.logger.log("info", f"Checked {total_collections} collections, removed {removed_collections} collections.")
        return any_removed
    
    def close(self):
        """
        Close the MongoDB connection.
        """
        if self.client:
            self.client.close()
            self.logger.log("info", "MongoDB connection closed.")
            self.client = None
            self.db = None


class ImageBinary:
    def encode_from_path(image_path: str):
        with open(image_path, 'rb') as f:
            image_data = bson.Binary(f.read())
            return image_data
        
    def encode_from_bytes(image_bytes: bytes) -> bytes:
        image_data = bson.Binary(image_bytes)
        return image_data
        
