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
