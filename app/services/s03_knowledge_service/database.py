"""
MongoDB database handler for S03 Knowledge Service.

Handles packages and faqs collections.
"""

import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from datetime import datetime
import traceback
from ...utils.db import serialize_mongo_doc

class MongoKnowledgeDB:
    """MongoDB database handler for knowledge storage."""
    
    def __init__(self, mongo_uri: Optional[str] = None, db_name: Optional[str] = None):
        """
        Initialize MongoDB connection.
        
        Args:
            mongo_uri: MongoDB connection string (default from MONGODB_URI env)
            db_name: Database name (default from MONGODB_DB_NAME env or 'telcenter_core_knowledge')
        """
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.db_name = db_name or os.getenv("MONGODB_DB_NAME", "telcenter_core_knowledge")
        
        self.client: MongoClient = MongoClient(self.mongo_uri)
        self.db: Database = self.client[self.db_name]
        
        # Collections
        self.packages: Collection = self.db["packages"]
        self.faqs: Collection = self.db["faqs"]
        
        self._create_indexes()
        
    def _create_indexes(self):
        """Create indexes for better query performance."""
        # Index on partner_id and service code for packages
        self.packages.create_index([("partner_id", 1), ("Mã dịch vụ", 1)], unique=True)
        
        # Index on partner_id for faqs
        self.faqs.create_index("partner_id")
        
    def store_packages(self, partner_id: str, packages_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store or update packages for a partner.
        
        Uses upsert to replace existing packages with same partner_id and service code.
        
        Args:
            partner_id: Partner identifier
            packages_data: List of package dictionaries
            
        Returns:
            Dictionary with counts: {"inserted": N, "updated": M}
        """
        inserted = 0
        updated = 0
        
        for package in packages_data:
            # Add partner_id and timestamp
            package["partner_id"] = partner_id
            package["updated_at"] = datetime.utcnow()

            package = serialize_mongo_doc(package)
            
            # Upsert based on partner_id and service code
            result = self.packages.update_one(
                {
                    "partner_id": partner_id,
                    "Mã dịch vụ": package.get("Mã dịch vụ")
                },
                {"$set": package},
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1
                
        return {"inserted": inserted, "updated": updated}
    
    def store_faqs(self, partner_id: str, faqs_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store or update FAQs for a partner.
        
        Replaces all FAQs for this partner (delete old, insert new).
        
        Args:
            partner_id: Partner identifier
            faqs_data: List of FAQ dictionaries with 'question' and 'answer'
            
        Returns:
            Dictionary with counts: {"deleted": N, "inserted": M}
        """
        # Delete existing FAQs for this partner
        delete_result = self.faqs.delete_many({"partner_id": partner_id})
        deleted = delete_result.deleted_count
        
        # Insert new FAQs
        if faqs_data:
            faqs_to_insert = []
            for faq in faqs_data:
                faq_doc = {
                    "partner_id": partner_id,
                    "question": faq.get("question", ""),
                    "answer": faq.get("answer", ""),
                    "created_at": datetime.utcnow()
                }

                faq_doc = serialize_mongo_doc(faq_doc)
                
                faqs_to_insert.append(faq_doc)
            
            insert_result = self.faqs.insert_many(faqs_to_insert)
            inserted = len(insert_result.inserted_ids)
        else:
            inserted = 0
            
        return {"deleted": deleted, "inserted": inserted}
    
    def get_all_packages(self) -> List[Dict[str, Any]]:
        """
        Retrieve all packages from all partners.
        
        Returns:
            List of package documents
        """
        packages = list(self.packages.find({}, {"_id": 0}))
        return packages
    
    def get_all_faqs(self) -> List[Dict[str, Any]]:
        """
        Retrieve all FAQs from all partners.
        
        Returns:
            List of FAQ documents
        """
        faqs = list(self.faqs.find({}, {"_id": 0}))
        return faqs
    
    def get_packages_by_partner(self, partner_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve packages for a specific partner.
        
        Args:
            partner_id: Partner identifier
            
        Returns:
            List of package documents
        """
        packages = list(self.packages.find({"partner_id": partner_id}, {"_id": 0}))
        return packages
    
    def get_faqs_by_partner(self, partner_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve FAQs for a specific partner.
        
        Args:
            partner_id: Partner identifier
            
        Returns:
            List of FAQ documents
        """
        faqs = list(self.faqs.find({"partner_id": partner_id}, {"_id": 0}))
        return faqs
    
    def close(self):
        """Close MongoDB connection."""
        print("MONGODB CLOSE CALLED FROM:")
        traceback.print_stack()
        self.client.close()
