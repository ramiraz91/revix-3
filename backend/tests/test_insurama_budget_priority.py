"""
Test for Insurama budget selection priority fix.
Bug: When multiple quotes exist for the same authorization number (e.g., 26BE001014),
the system was selecting the first one without checking if it was cancelled vs accepted.

Fix: Modified find_budget_by_service_code to prioritize:
1. Accepted budgets (status=3)
2. Active budgets (status != 7 cancelled)
3. First result (fallback)

Additional fix: Status can come as string from API, so we normalize to int.

Sumbroker status codes:
1=Pending, 2=Sent, 3=Accepted, 4=Modified, 5=Repaired, 6=Delivered, 7=Cancelled
"""
import pytest


def create_mock_budget(identifier: str, status, budget_id: int = 1) -> dict:
    """Create a mock Sumbroker budget structure. Status can be int or string."""
    status_texts = {1: 'Pendiente', 2: 'Enviado', 3: 'Aceptado', 
                   4: 'Modificado', 5: 'Reparado', 6: 'Entregado', 
                   7: 'Cancelado'}
    status_int = int(status) if status is not None else None
    return {
        'id': budget_id,
        'status': status,  # Keep original (could be string or int)
        'status_text': status_texts.get(status_int, 'Desconocido'),
        'claim_budget': {
            'policy_risk_claim': {
                'identifier': identifier
            }
        }
    }


def find_best_budget(budgets: list, codigo: str) -> dict:
    """
    Replicated logic from scraper.py find_budget_by_service_code.
    Used for unit testing without async/network dependencies.
    """
    if not budgets:
        return None
    
    # Filter budgets that match the exact claim identifier
    exact_matches = []
    for b in budgets:
        claim = b.get('claim_budget') or {}
        prc = claim.get('policy_risk_claim') or {}
        if prc.get('identifier') == codigo:
            exact_matches.append(b)
    
    # If we have exact matches, prioritize by status
    candidates = exact_matches if exact_matches else budgets
    
    # Priority 1: Find accepted budget (status 3)
    for b in candidates:
        # Status can be string or int - normalize to int
        status_raw = b.get('status')
        status = int(status_raw) if status_raw is not None else None
        if status == 3:
            return b
    
    # Priority 2: Find any active budget (not cancelled, status != 7)
    for b in candidates:
        status_raw = b.get('status')
        status = int(status_raw) if status_raw is not None else None
        if status != 7:
            return b
    
    # Priority 3: Return first result (even if cancelled, as last resort)
    return candidates[0] if candidates else None


class TestInsurarmaBudgetPriority:
    """Test budget selection priority when multiple budgets exist."""
    
    def test_accepted_over_cancelled(self):
        """Bug scenario: Cancelled budget should NOT be selected over accepted one."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget(codigo, 7, budget_id=1),  # Cancelled (first in list)
            create_mock_budget(codigo, 3, budget_id=2),  # Accepted (second)
        ]
        
        result = find_best_budget(budgets, codigo)
        assert result['id'] == 2, "Should select the accepted budget (id=2)"
    
    def test_accepted_over_cancelled_with_string_status(self):
        """Real API scenario: Status comes as string, not int."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget(codigo, "7", budget_id=401395),  # Cancelled as STRING
            create_mock_budget(codigo, "3", budget_id=401618),  # Accepted as STRING
        ]
        
        result = find_best_budget(budgets, codigo)
        assert result['id'] == 401618, "Should select accepted budget even with string status"
    
    def test_pending_over_cancelled(self):
        """Pending budget should be selected over cancelled."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget(codigo, 7, budget_id=1),  # Cancelled
            create_mock_budget(codigo, 1, budget_id=2),  # Pending
        ]
        
        result = find_best_budget(budgets, codigo)
        status_raw = result.get('status')
        status = int(status_raw) if status_raw is not None else None
        assert status == 1, "Should select pending (status=1) over cancelled"
    
    def test_accepted_is_highest_priority(self):
        """Accepted (status=3) should be selected even if pending exists."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget(codigo, 1, budget_id=1),  # Pending
            create_mock_budget(codigo, 3, budget_id=2),  # Accepted
            create_mock_budget(codigo, 7, budget_id=3),  # Cancelled
        ]
        
        result = find_best_budget(budgets, codigo)
        status_raw = result.get('status')
        status = int(status_raw) if status_raw is not None else None
        assert status == 3, "Should select accepted (status=3) as highest priority"
    
    def test_all_cancelled_returns_first(self):
        """If all budgets are cancelled, return first one."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget(codigo, 7, budget_id=1),
            create_mock_budget(codigo, 7, budget_id=2),
        ]
        
        result = find_best_budget(budgets, codigo)
        assert result['id'] == 1
    
    def test_single_budget_returned(self):
        """Single budget should be returned regardless of status."""
        codigo = '26BE001014'
        
        # Single accepted
        result1 = find_best_budget([create_mock_budget(codigo, 3, 1)], codigo)
        status1 = int(result1.get('status'))
        assert status1 == 3
        
        # Single cancelled
        result2 = find_best_budget([create_mock_budget(codigo, 7, 1)], codigo)
        status2 = int(result2.get('status'))
        assert status2 == 7
    
    def test_empty_list_returns_none(self):
        """Empty budget list should return None."""
        result = find_best_budget([], '26BE001014')
        assert result is None
    
    def test_mixed_status_with_exact_match(self):
        """Test with mixed statuses ensuring exact identifier match."""
        codigo = '26BE001014'
        budgets = [
            create_mock_budget('DIFFERENT_CODE', 3, budget_id=1),  # Different code, accepted
            create_mock_budget(codigo, 7, budget_id=2),  # Our code, cancelled
            create_mock_budget(codigo, 3, budget_id=3),  # Our code, accepted
        ]
        
        result = find_best_budget(budgets, codigo)
        assert result['id'] == 3, "Should select exact match with accepted status"
    
    def test_real_api_response_scenario(self):
        """Test with exact structure from real API response."""
        codigo = '26BE001014'
        # Simulating real API response structure
        budgets = [
            {
                'id': 401395,
                'status': 7,  # int
                'status_text': 'Cancelado',
                'price': '130.00',
                'claim_budget': {
                    'policy_risk_claim': {'identifier': codigo}
                }
            },
            {
                'id': 401618,
                'status': 3,  # int
                'status_text': 'Aceptado',
                'price': '150.00',
                'claim_budget': {
                    'policy_risk_claim': {'identifier': codigo}
                }
            }
        ]
        
        result = find_best_budget(budgets, codigo)
        assert result['id'] == 401618, "Should select budget 401618 (Aceptado)"
        assert result['price'] == '150.00', "Should have correct price"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
