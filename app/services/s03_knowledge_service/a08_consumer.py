"""
A08 Event Consumer for S03 Knowledge Service.

Consumes store_validated_knowledge events from S05 (Core Knowledge Validator Service).
Downloads JSON from SeaweedFS and stores in MongoDB.
"""

import os
import json
import requests
from typing import Dict, Any, Callable
from app.services.MessageQueueService import MessageQueueService


class A08Consumer:
    """Consumes A08 events to store validated knowledge."""
    
    def __init__(
        self,
        mq_service: MessageQueueService,
        seaweed_master_url: str | None = None,
        on_knowledge_stored: Callable[[str, Dict[str, Any]], None] | None = None
    ):
        """
        Initialize A08 consumer.
        
        Args:
            mq_service: MessageQueueService instance
            seaweed_master_url: SeaweedFS master URL (default from env)
            on_knowledge_stored: Callback(partner_id, knowledge_data) after storing
        """
        self.mq_service = mq_service
        self.seaweed_master_url = seaweed_master_url or os.getenv(
            "SEAWEED_MASTER_URL",
            "http://localhost:9333"
        )
        self.on_knowledge_stored = on_knowledge_stored
        
        # Get queue name from env
        self.event_queue = os.getenv("KNOWLEDGE_STORE_EVENT_QUEUE", "knowledge_store_events")
        
        # Declare queue
        self.mq_service.declare_queue(self.event_queue)
        
    def register_callbacks(self):
        """Start consuming A08 events."""
        print(f"[A08Consumer] Registering callback on queue: {self.event_queue}")
        self.mq_service.register_callback(self.event_queue, self._handle_event)
        
    def _handle_event(self, message: Dict[str, Any]):
        """
        Handle incoming store_validated_knowledge event.
        
        Expected message format:
        {
          "event": "store_validated_knowledge",
          "data": {
            "partner_id": "viettel_partner_001",
            "seaweed_file_id": "3,01234567",
            "validated_at": "2025-12-08T10:30:00Z"
          }
        }
        """
        print(f"[A08Consumer] Received event: {message}")
        
        try:
            event_name = message.get("event")
            if event_name != "store_validated_knowledge":
                print(f"[A08Consumer] Unknown event type: {event_name}")
                return
            
            data = message.get("data", {})
            partner_id = data.get("partner_id")
            seaweed_file_id = data.get("seaweed_file_id")
            
            if not partner_id or not seaweed_file_id:
                raise ValueError("Missing required fields: partner_id or seaweed_file_id")
            
            # Download JSON from SeaweedFS
            knowledge_data = self._download_from_seaweed(seaweed_file_id)
            
            # Trigger callback if registered
            if self.on_knowledge_stored:
                self.on_knowledge_stored(partner_id, knowledge_data)
            
            print(f"[A08Consumer] Successfully processed knowledge for partner: {partner_id}")
            
        except Exception as e:
            print(f"[A08Consumer] Error processing event: {e}")
            raise
    
    def _download_from_seaweed(self, file_id: str) -> Dict[str, Any]:
        """
        Download JSON file from SeaweedFS.
        
        Args:
            file_id: SeaweedFS file identifier (e.g., "3,01234567")
            
        Returns:
            Parsed JSON data
        """
        file_url = f"{self.seaweed_master_url}/{file_id}"
        
        print(f"[A08Consumer] Downloading from SeaweedFS: {file_url}")
        
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        
        return response.json()
