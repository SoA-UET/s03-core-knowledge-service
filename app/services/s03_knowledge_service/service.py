"""
S03 Knowledge Service - Main Orchestrator

Coordinates A08 event consumption, database storage, and A01 updates to S02.
"""

import os
import threading
from typing import Dict, Any
from app.services.MessageQueueService import MessageQueueService
from .database import MongoKnowledgeDB
from .a08_consumer import A08Consumer
from .a01_client import A01Client


class KnowledgeService:
    """
    Main Knowledge Service orchestrator.
    
    Flow:
    1. Receive validated knowledge via A08 event from S05
    2. Download JSON from SeaweedFS
    3. Store in MongoDB (packages and faqs collections)
    4. Send updates to S02 via A01 RPC
    """
    
    def __init__(
        self,
        rabbitmq_url: str | None = None,
        mongo_uri: str | None = None,
        seaweed_master_url: str | None = None
    ):
        """
        Initialize Knowledge Service.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL (default from env)
            mongo_uri: MongoDB connection URI (default from env)
            seaweed_master_url: SeaweedFS master URL (default from env)
        """
        print("[S03 KnowledgeService] Initializing...")
        
        # Initialize database
        self.db = MongoKnowledgeDB(mongo_uri=mongo_uri)
        print("[S03 KnowledgeService] MongoDB connected")
        
        # Initialize message queue service
        self.mq_service = MessageQueueService(rabbitmq_url=rabbitmq_url)
        print("[S03 KnowledgeService] RabbitMQ connected")
        
        # Initialize A01 client (for sending to S02)
        self.a01_client = A01Client(self.mq_service)
        
        # Initialize A08 consumer (for receiving from S05)
        self.a08_consumer = A08Consumer(
            mq_service=self.mq_service,
            seaweed_master_url=seaweed_master_url,
            on_knowledge_stored=self._handle_knowledge_stored
        )
        
        print("[S03 KnowledgeService] Initialized successfully")
    
    def _handle_knowledge_stored(self, partner_id: str, knowledge_data: Dict[str, Any]):
        """
        Handle validated knowledge storage.
        
        Called by A08Consumer after downloading JSON from SeaweedFS.
        
        Args:
            partner_id: Partner identifier
            knowledge_data: JSON data with 'packages' and 'faqs' arrays
        """
        print(f"[S03 KnowledgeService] Storing knowledge for partner: {partner_id}")
        
        try:
            # Extract packages and faqs from knowledge data
            packages = knowledge_data.get("packages", [])
            faqs = knowledge_data.get("faqs", [])
            
            # Store in MongoDB
            if packages:
                package_result = self.db.store_packages(partner_id, packages)
                print(f"[S03 KnowledgeService] Packages stored: {package_result}")
            
            if faqs:
                faq_result = self.db.store_faqs(partner_id, faqs)
                print(f"[S03 KnowledgeService] FAQs stored: {faq_result}")
            
            # Send updates to S02 via A01
            # Determine source name from partner_id (simplification)
            source = partner_id.replace("_partner_", " ").title()
            
            if packages:
                self.a01_client.update_dataframe(source, packages)
                print(f"[S03 KnowledgeService] Sent packages to S02 for source: {source}")
            
            if faqs:
                self.a01_client.update_faqs(source, faqs)
                print(f"[S03 KnowledgeService] Sent FAQs to S02 for source: {source}")
            
            print(f"[S03 KnowledgeService] Successfully processed knowledge for partner: {partner_id}")
            
        except Exception as e:
            print(f"[S03 KnowledgeService] Error handling knowledge storage: {e}")
            raise
    
    def start(self):
        """Start the Knowledge Service."""
        print("[S03 KnowledgeService] Starting service...")
        
        # Start A08 consumer
        self.a08_consumer.start_consuming()
        
        # Start consuming (blocking)
        print("[S03 KnowledgeService] Listening for A08 events...")
        self.mq_service.start_consuming()
    
    def stop(self):
        """Stop the Knowledge Service and cleanup resources."""
        print("[S03 KnowledgeService] Stopping service...")
        self.db.close()
        print("[S03 KnowledgeService] Stopped")


def main():
    """
    Main entry point for running S03 Knowledge Service standalone.
    """
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create and start service
    service = KnowledgeService()
    
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n[S03 KnowledgeService] Received interrupt signal")
        service.stop()
    except Exception as e:
        print(f"[S03 KnowledgeService] Fatal error: {e}")
        service.stop()
        raise


if __name__ == "__main__":
    main()
