from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class RecoveryActionBase(BaseModel):
    entity_type: str
    entity_id: str
    root_cause: Optional[str] = None
    action_type: str
    
class RecoveryActionCreate(RecoveryActionBase):
    pass
    
class RecoveryActionResponse(RecoveryActionBase):
    id: str
    decided_at: datetime
    executed_at: Optional[datetime] = None
    outcome: Optional[str] = None
    
    class Config:
        from_attributes = True

class QueueItem(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    amount: float
    root_cause: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    next_action: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    attempt_count: int
    max_attempts: int
    customer_id: str
    created_at: datetime
    expected_recovery_value: Optional[float] = None
    days_overdue: Optional[int] = None
    
class RecoveryQueueResponse(BaseModel):
    items: List[QueueItem]
    total: int
