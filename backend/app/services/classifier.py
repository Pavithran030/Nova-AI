from typing import Tuple

def classify_root_cause(error_code: str, status: str) -> Tuple[str, float, str]:
    if status == 'abandoned':
        return 'ABANDONMENT', 0.85, 'Status is abandoned'
    if status == 'overdue':
        return 'OVERDUE', 0.85, 'Status is overdue'
        
    if not error_code:
        return 'BANK_TIMEOUT', 0.65, 'No error code provided, defaulting'
        
    error_code = error_code.upper()
    
    if any(keyword in error_code for keyword in ['INSUFF', 'BAL', 'NSF']):
        return 'INSUFFICIENT_FUNDS', 0.85, 'Matches insufficient funds pattern'
    if any(keyword in error_code for keyword in ['TIMEOUT', 'TIME']):
        return 'BANK_TIMEOUT', 0.85, 'Matches bank timeout pattern'
    if any(keyword in error_code for keyword in ['EXPIRED', 'EXP']):
        return 'CARD_EXPIRED', 0.85, 'Matches card expired pattern'
    if any(keyword in error_code for keyword in ['REVOKE', 'MANDATE']):
        return 'MANDATE_REVOKED', 0.85, 'Matches mandate revoked pattern'
    if any(keyword in error_code for keyword in ['RISK', 'FRAUD', 'DECLINE']):
        return 'RISK_DECLINE', 0.85, 'Matches risk decline pattern'
    if any(keyword in error_code for keyword in ['NETWORK', 'CONN']):
        return 'NETWORK_ERROR', 0.85, 'Matches network error pattern'
        
    return 'BANK_TIMEOUT', 0.65, 'Fallback applied'
