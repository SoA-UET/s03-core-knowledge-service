# S03 Knowledge Service

Core knowledge storage service that manages packages (gói cước) and FAQs for the Telcenter system.

## Architecture

```
S05 Validator → [A08 Event] → S03 Knowledge Service → [A01 RPC] → S02 AI Agent
                                    ↓
                               MongoDB
                          (packages + faqs)
```

## Components

### 1. Database Layer (`database.py`)
- **MongoKnowledgeDB**: MongoDB handler
- Collections:
  - `packages`: Service packages (gói cước) with unique index on (partner_id, Mã dịch vụ)
  - `faqs`: Frequently asked questions with partner_id index
- Operations:
  - `store_packages()`: Upsert packages by partner_id + service code
  - `store_faqs()`: Replace all FAQs for partner_id
  - Getters: `get_all_packages()`, `get_all_faqs()`, etc.

### 2. A08 Consumer (`a08_consumer.py`)
- **A08Consumer**: Receives validated knowledge from S05
- Queue: `knowledge_store_events`
- Event: `store_validated_knowledge`
- Flow:
  1. Receive event with `seaweed_file_id`
  2. Download JSON from SeaweedFS
  3. Call callback `on_knowledge_stored(partner_id, knowledge_data)`

### 3. A01 Client (`a01_client.py`)
- **A01Client**: Sends knowledge updates to S02 AI Agent
- Queues: `telcenter_ai_agent_requests`, `telcenter_ai_agent_responses`
- Methods:
  - `update_dataframe(source, packages)`: Send packages list
  - `update_faqs(source, faqs)`: Send FAQs list
- Pattern: RPC with response waiting (30s timeout)

### 4. Main Orchestrator (`service.py`)
- **KnowledgeService**: Coordinates all components
- Flow:
  1. Receive A08 event (validated knowledge)
  2. Store in MongoDB (packages + faqs)
  3. Send updates to S02 via A01

## Configuration

Environment variables (see `.env.example`):

```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=telcenter_core_knowledge

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# SeaweedFS
SEAWEED_MASTER_URL=http://localhost:9333

# A08 Event Queue
KNOWLEDGE_STORE_EVENT_QUEUE=knowledge_store_events

# A01 RPC Queues
TELCENTER_AI_AGENT_REQUESTS_QUEUE=telcenter_ai_agent_requests
TELCENTER_AI_AGENT_RESPONSES_QUEUE=telcenter_ai_agent_responses
```

## Usage

### Run as standalone service:

```bash
python -m app.services.s03_knowledge_service.service
```

### Run with all services:

```bash
python -m app
```

### Integration in code:

```python
from app.services.s03_knowledge_service import KnowledgeService

# Initialize
service = KnowledgeService()

# Start (blocking)
service.start()

# Or run in thread
import threading
thread = threading.Thread(target=service.start, daemon=False)
thread.start()
```

## Data Flow Example

### 1. S05 sends validated knowledge (A08 Event):
```json
{
  "event": "store_validated_knowledge",
  "data": {
    "partner_id": "vnpt_partner_1",
    "seaweed_file_id": "3,01234567890",
    "validated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2. S03 downloads from SeaweedFS:
```bash
GET http://localhost:9333/3,01234567890
```

Response:
```json
{
  "packages": [
    {
      "Mã dịch vụ": "ST70K",
      "Tên gói cước": "Gói ST70K",
      "Giá cước (đ/tháng)": 70000,
      "Dung lượng data": "3 GB/ngày",
      "Gọi thoại": "Miễn phí nội mạng"
    }
  ],
  "faqs": [
    {
      "question": "Cách đăng ký gói ST70K?",
      "answer": "Soạn ST70K gửi 900"
    }
  ]
}
```

### 3. S03 stores in MongoDB:
- Packages → `packages` collection (upsert by partner_id + service code)
- FAQs → `faqs` collection (replace all for partner_id)

### 4. S03 sends to S02 (A01 RPC):
```json
// update_dataframe request
{
  "method": "update_dataframe",
  "params": {
    "source": "VNPT Partner 1",
    "packages": [...]
  }
}

// update_faqs request
{
  "method": "update_faqs",
  "params": {
    "source": "VNPT Partner 1",
    "faqs": [...]
  }
}
```

## Dependencies

- `pymongo`: MongoDB driver
- `pika`: RabbitMQ client
- `requests`: HTTP client for SeaweedFS
- `python-dotenv`: Environment configuration

## Related Services

- **S05 Knowledge Validator Service**: Validates submissions, emits A08 events
- **S02 Consultant AI Agent**: Receives A01 updates, uses knowledge for consultations

## API References

- [A08 API Specification](../../../docs/api_groups/A08.md)
- [A01 API Specification](../../../docs/api_groups/A01.md)
- [S03 Service Specification](../../../docs/services/core/S03_Knowledge_Service.md)
