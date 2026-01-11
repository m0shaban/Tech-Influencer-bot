"""
Bot Registry - Central directory for running bot instances.
Allows Master Controller and AutoPublisher to access Worker Bots.
"""
from typing import Dict, Any, Optional

class BotRegistry:
    _instance = None
    _workers: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def register_worker(cls, brand_key: str, worker_instance: Any):
        """Register a running worker bot instance."""
        cls._workers[brand_key.lower()] = worker_instance
        print(f"[REGISTRY] Registered worker: {brand_key}")

    @classmethod
    def get_worker(cls, brand_key: str) -> Optional[Any]:
        """Get a worker instance by brand key."""
        return cls._workers.get(brand_key.lower())

    @classmethod
    def get_all_workers(cls) -> Dict[str, Any]:
        """Get all registered workers."""
        return cls._workers
