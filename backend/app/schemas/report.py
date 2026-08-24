from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ReportSummary(BaseModel):
    total_at_risk: float
    total_recovered: float
    recovery_rate: float
    active_cases: int
    by_root_cause: Dict[str, Any]
    trend: List[Dict[str, Any]]
    recent_actions: List[Dict[str, Any]]

class BaselineComparison(BaseModel):
    baseline: Dict[str, Any]
    agent: Dict[str, Any]
    delta: Dict[str, Any]

class StrategyPerformance(BaseModel):
    channels: List[Dict[str, Any]]
