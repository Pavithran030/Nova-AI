from datetime import datetime

class PromiseTracker:
    def __init__(self):
        self.promises = {}
        
    def record_promise(self, entity_id: str, promised_date: datetime, amount: float):
        self.promises[entity_id] = {
            "promised_date": promised_date,
            "amount": amount,
            "status": "pending"
        }
        
    def check_promise(self, entity_id: str) -> str:
        if entity_id not in self.promises:
            return "not_found"
        # Dummy implementation
        return self.promises[entity_id]["status"]

tracker = PromiseTracker()
