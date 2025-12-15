"""
Telcenter Base Service - Main Entry Point

This module starts all active microservices.
"""

import os
import sys
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import services
from app.services.s03_knowledge_service import KnowledgeService


def main():
    """
    Main application entry point.
    
    Starts all configured microservices.
    """
    print("=" * 80)
    print("Telcenter Base Service - Starting...")
    print("=" * 80)
    
    # Initialize services
    services = []
    
    # S03 Knowledge Service
    try:
        print("\n[Main] Initializing S03 Knowledge Service...")
        s03_service = KnowledgeService()
        services.append(("S03 Knowledge Service", s03_service))
        print("[Main] S03 Knowledge Service initialized")
    except Exception as e:
        print(f"[Main] ERROR: Failed to initialize S03 Knowledge Service: {e}")
        sys.exit(1)
    
    # Add other services here as they are implemented
    # Example:
    # s02_service = ConsultantAIAgent()
    # services.append(("S02 Consultant AI Agent", s02_service))
    
    print("\n" + "=" * 80)
    print(f"Starting {len(services)} service(s)...")
    print("=" * 80 + "\n")
    
    # Start all services
    service_threads = []
    
    for service_name, service in services:
        def start_service(name, svc):
            try:
                print(f"[Main] Starting {name}...")
                svc.start()
            except Exception as e:
                print(f"[Main] ERROR: {name} crashed: {e}")
        
        thread = threading.Thread(
            target=start_service,
            args=(service_name, service),
            daemon=False,
            name=service_name
        )
        thread.start()
        service_threads.append((service_name, thread))
    
    print("\n" + "=" * 80)
    print("All services started successfully!")
    print("Press Ctrl+C to stop all services")
    print("=" * 80 + "\n")
    
    # Wait for all threads
    try:
        for service_name, thread in service_threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("Received shutdown signal (Ctrl+C)")
        print("=" * 80)
        
        # Cleanup services
        for service_name, service in services:
            try:
                print(f"[Main] Stopping {service_name}...")
                service.stop()
            except Exception as e:
                print(f"[Main] Error stopping {service_name}: {e}")
        
        print("\n[Main] All services stopped. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
