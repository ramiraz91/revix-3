"""
Test Suite for ARIA Agent (Iteration 50)
Tests the AI agent endpoints: /api/agent/summary, /api/agent/chat, /api/agent/alerts
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestARIAAgentEndpoints:
    """Test ARIA Agent API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        # Login with master credentials
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ramiraz91@gmail.com", "password": "temp123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        yield
    
    # ===== GET /api/agent/summary Tests =====
    
    def test_agent_summary_returns_200(self):
        """Test GET /api/agent/summary returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/agent/summary",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_agent_summary_structure(self):
        """Test GET /api/agent/summary returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/agent/summary",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level keys
        assert "summary" in data, "Missing 'summary' key"
        assert "alerts" in data, "Missing 'alerts' key"
        assert "timestamp" in data, "Missing 'timestamp' key"
        
        # Check summary structure
        summary = data["summary"]
        assert "peticiones" in summary, "Missing 'peticiones' in summary"
        assert "ordenes" in summary, "Missing 'ordenes' in summary"
        assert "alertas" in summary, "Missing 'alertas' in summary"
        
        # Check peticiones structure
        peticiones = summary["peticiones"]
        assert "total" in peticiones
        assert "pendientes_llamar" in peticiones
        assert "nuevas_hoy" in peticiones
        assert "fuera_sla_2h" in peticiones
        
        # Check ordenes structure
        ordenes = summary["ordenes"]
        assert "total" in ordenes
        assert "por_estado" in ordenes
        assert "nuevas_hoy" in ordenes
    
    def test_agent_summary_requires_auth(self):
        """Test GET /api/agent/summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/agent/summary")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    # ===== GET /api/agent/alerts Tests =====
    
    def test_agent_alerts_returns_200(self):
        """Test GET /api/agent/alerts returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/agent/alerts",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_agent_alerts_structure(self):
        """Test GET /api/agent/alerts returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/agent/alerts",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data, "Missing 'alerts' key"
        assert "total" in data, "Missing 'total' key"
        assert "timestamp" in data, "Missing 'timestamp' key"
        assert isinstance(data["alerts"], list), "'alerts' should be a list"
    
    # ===== POST /api/agent/chat Tests =====
    
    def test_agent_chat_returns_200(self):
        """Test POST /api/agent/chat returns 200 OK"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={"message": "Hola"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_agent_chat_response_structure(self):
        """Test POST /api/agent/chat returns correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={"message": "Hola ARIA"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data, "Missing 'response' key"
        assert "conversation_id" in data, "Missing 'conversation_id' key"
        assert "functions_executed" in data, "Missing 'functions_executed' key"
        assert "alerts" in data, "Missing 'alerts' key"
        assert "timestamp" in data, "Missing 'timestamp' key"
        
        # Response should be a non-empty string
        assert isinstance(data["response"], str), "'response' should be a string"
        assert len(data["response"]) > 0, "'response' should not be empty"
    
    def test_agent_chat_executes_functions(self):
        """Test POST /api/agent/chat executes functions when needed"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={"message": "Dame un resumen del sistema"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have executed obtener_resumen_sistema function
        functions = data.get("functions_executed", [])
        assert len(functions) > 0, "Expected at least one function to be executed"
        
        # Check function structure
        func = functions[0]
        assert "function" in func, "Missing 'function' key in executed function"
        assert "result" in func, "Missing 'result' key in executed function"
    
    def test_agent_chat_conversation_persistence(self):
        """Test POST /api/agent/chat maintains conversation context"""
        # First message
        response1 = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={"message": "Hola, soy un test"}
        )
        assert response1.status_code == 200
        conv_id = response1.json().get("conversation_id")
        assert conv_id, "Should return conversation_id"
        
        # Second message with same conversation_id
        response2 = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={"message": "¿Recuerdas mi mensaje anterior?", "conversation_id": conv_id}
        )
        assert response2.status_code == 200
        assert response2.json().get("conversation_id") == conv_id, "Should maintain same conversation_id"
    
    def test_agent_chat_requires_auth(self):
        """Test POST /api/agent/chat requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            json={"message": "Hola"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_agent_chat_requires_message(self):
        """Test POST /api/agent/chat requires message field"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=self.headers,
            json={}
        )
        assert response.status_code == 422, f"Expected 422 for missing message, got {response.status_code}"
    
    # ===== Quick Action Tests =====
    
    def test_quick_action_call_pending(self):
        """Test POST /api/agent/quick-action/call-pending"""
        response = requests.post(
            f"{BASE_URL}/api/agent/quick-action/call-pending",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "peticiones" in data
        assert "total" in data
        assert "mensaje" in data
    
    def test_quick_action_validation_pending(self):
        """Test POST /api/agent/quick-action/validation-pending"""
        response = requests.post(
            f"{BASE_URL}/api/agent/quick-action/validation-pending",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "ordenes" in data
        assert "total" in data
    
    def test_quick_action_stats_hoy(self):
        """Test POST /api/agent/quick-action/stats/hoy"""
        response = requests.post(
            f"{BASE_URL}/api/agent/quick-action/stats/hoy",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "periodo" in data
        assert "peticiones" in data
        assert "ordenes" in data
    
    def test_quick_action_stats_semana(self):
        """Test POST /api/agent/quick-action/stats/semana"""
        response = requests.post(
            f"{BASE_URL}/api/agent/quick-action/stats/semana",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"] == "semana"
    
    def test_quick_action_stats_mes(self):
        """Test POST /api/agent/quick-action/stats/mes"""
        response = requests.post(
            f"{BASE_URL}/api/agent/quick-action/stats/mes",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["periodo"] == "mes"
    
    # ===== Conversations Tests =====
    
    def test_list_conversations(self):
        """Test GET /api/agent/conversations"""
        response = requests.get(
            f"{BASE_URL}/api/agent/conversations",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
    
    def test_get_conversation_not_found(self):
        """Test GET /api/agent/conversations/{id} returns 404 for non-existent"""
        response = requests.get(
            f"{BASE_URL}/api/agent/conversations/non-existent-id",
            headers=self.headers
        )
        assert response.status_code == 404


class TestARIAAgentPermissions:
    """Test ARIA Agent permission requirements"""
    
    def test_tecnico_cannot_access_agent_summary(self):
        """Test that tecnico role cannot access agent summary"""
        # Login as tecnico
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "tecnico@techrepair.local", "password": "Tecnico2026!"}
        )
        if login_response.status_code != 200:
            pytest.skip("Tecnico user not available")
        
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/agent/summary",
            headers=headers
        )
        # Should be forbidden for tecnico
        assert response.status_code == 403, f"Expected 403 for tecnico, got {response.status_code}"
    
    def test_admin_can_access_agent_summary(self):
        """Test that admin role can access agent summary"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@techrepair.local", "password": "Admin2026!"}
        )
        if login_response.status_code != 200:
            pytest.skip("Admin user not available")
        
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/agent/summary",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
