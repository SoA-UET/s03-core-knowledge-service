"""
A01 RPC Client for S03 Knowledge Service.

Sends knowledge updates to S02 Consultant AI Agent via RabbitMQ RPC.
"""

import os
import uuid
import json
import threading
from typing import Dict, Any, List
from app.services.MessageQueueService import MessageQueueService


class A01Client:
    """RPC client for sending knowledge updates to S02 via A01."""
    
    def __init__(self, mq_service: MessageQueueService):
        """
        Initialize A01 RPC client.
        
        Args:
            mq_service: MessageQueueService instance
        """
        self.mq_service = mq_service
        
        # Get queue names from env
        self.request_queue = os.getenv(
            "TELCENTER_AI_AGENT_REQUESTS_QUEUE",
            "telcenter_ai_agent_requests"
        )
        self.response_queue = os.getenv(
            "TELCENTER_AI_AGENT_RESPONSES_QUEUE",
            "telcenter_ai_agent_responses"
        )
        
        # Declare queues
        self.mq_service.declare_queue(self.request_queue)
        self.mq_service.declare_queue(self.response_queue)
        
        # Response storage
        self.responses: Dict[str, Any] = {}
        self.response_lock = threading.Lock()
        
        # Start response consumer in background thread
        self._start_response_consumer()
        
    def _start_response_consumer(self):
        """Start consuming responses in a background thread."""
        def consume_responses():
            # Clone connection for thread safety
            mq_clone = self.mq_service.clone()
            mq_clone.register_callback(self.response_queue, self._handle_response)
            mq_clone.start_consuming()
        
        thread = threading.Thread(target=consume_responses, daemon=True)
        thread.start()
        print(f"[A01Client] Started response consumer on queue: {self.response_queue}")
    
    def _handle_response(self, message: Dict[str, Any]):
        """Handle RPC response."""
        request_id = message.get("id")
        if request_id:
            with self.response_lock:
                self.responses[request_id] = message
    
    def _wait_for_response(self, request_id: str, timeout: float = 600.0) -> Dict[str, Any]:
        """Wait for RPC response."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.response_lock:
                if request_id in self.responses:
                    response = self.responses.pop(request_id)
                    return response
            time.sleep(0.1)
        
        raise TimeoutError(f"No response received for request {request_id} within {timeout}s")
    
    def update_dataframe(self, source: str, packages: List[Dict[str, Any]]) -> str:
        """
        Send packages update to S02 via A01.
        
        Args:
            source: Partner source name (e.g., "Viettel")
            packages: List of package dictionaries
            
        Returns:
            Response content ("OK" on success)
        """
        request_id = str(uuid.uuid4())
        
        request = {
            "method": "update_dataframe",
            "params": {
                "source": source,
                "df": packages
            },
            "id": request_id
        }
        
        print(f"[A01Client] Sending update_dataframe request: {request_id}")
        self.mq_service.publish_message(self.request_queue, request)
        
        # Wait for response
        response = self._wait_for_response(request_id)
        
        result = response.get("result", {})
        status = result.get("status")
        content = result.get("content")
        
        if status == "error":
            raise RuntimeError(f"A01 update_dataframe failed: {content}")
        
        print(f"[A01Client] update_dataframe success: {content}")
        return content
    
    def update_faqs(self, source: str, faqs: List[Dict[str, Any]]) -> str:
        """
        Send FAQs update to S02 via A01.
        
        Args:
            source: Partner source name (e.g., "Viettel")
            faqs: List of FAQ dictionaries with 'question' and 'answer'
            
        Returns:
            Response content ("OK" on success)
        """
        request_id = str(uuid.uuid4())
        
        request = {
            "method": "update_faqs",
            "params": {
                "source": source,
                "faqs": faqs
            },
            "id": request_id
        }
        
        print(f"[A01Client] Sending update_faqs request: {request_id}")
        self.mq_service.publish_message(self.request_queue, request)
        
        # Wait for response
        response = self._wait_for_response(request_id)
        
        result = response.get("result", {})
        status = result.get("status")
        content = result.get("content")
        
        if status == "error":
            raise RuntimeError(f"A01 update_faqs failed: {content}")
        
        print(f"[A01Client] update_faqs success: {content}")
        return content
