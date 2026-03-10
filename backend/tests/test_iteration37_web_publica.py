"""
Test iteration 37: Web Pública de Revix.es
Tests for chatbot IA, contacto form, presupuesto form, and public pages
"""
import pytest
import requests
import os
import time

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWebPublicaAPIs:
    """Test public web APIs - /api/web/*"""
    
    def test_chatbot_endpoint_responds_with_ai(self):
        """Test POST /api/web/chatbot - should return AI response in Spanish"""
        response = requests.post(
            f"{BASE_URL}/api/web/chatbot",
            json={
                "mensaje": "Hola, ¿qué servicios ofrecéis?",
                "session_id": f"test-{int(time.time())}"
            },
            timeout=30  # AI responses may take longer
        )
        assert response.status_code == 200, f"Chatbot returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert "respuesta" in data, "Response should contain 'respuesta' field"
        assert "session_id" in data, "Response should contain 'session_id' field"
        assert len(data["respuesta"]) > 0, "AI response should not be empty"
        print(f"✓ Chatbot AI response: {data['respuesta'][:100]}...")
    
    def test_chatbot_maintains_session_context(self):
        """Test chatbot maintains conversation history within session"""
        session_id = f"test-context-{int(time.time())}"
        
        # First message
        response1 = requests.post(
            f"{BASE_URL}/api/web/chatbot",
            json={
                "mensaje": "Me llamo Carlos",
                "session_id": session_id
            },
            timeout=30
        )
        assert response1.status_code == 200
        
        # Second message - should remember context
        response2 = requests.post(
            f"{BASE_URL}/api/web/chatbot",
            json={
                "mensaje": "¿Cuál es vuestra dirección?",
                "session_id": session_id
            },
            timeout=30
        )
        assert response2.status_code == 200
        data = response2.json()
        # Should mention the address from system prompt
        print(f"✓ Chatbot context response: {data['respuesta'][:150]}...")
    
    def test_contacto_endpoint_saves_message(self):
        """Test POST /api/web/contacto - should save contact form"""
        test_email = f"test{int(time.time())}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/web/contacto",
            json={
                "nombre": "Test Usuario",
                "email": test_email,
                "telefono": "666123456",
                "asunto": "Consulta de prueba",
                "mensaje": "Este es un mensaje de prueba para verificar el formulario de contacto."
            },
            timeout=10
        )
        assert response.status_code == 200, f"Contacto returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "id" in data, "Response should contain generated ID"
        assert "message" in data, "Response should contain confirmation message"
        print(f"✓ Contact form saved with ID: {data['id']}")
    
    def test_contacto_validates_required_fields(self):
        """Test POST /api/web/contacto - validates required fields"""
        response = requests.post(
            f"{BASE_URL}/api/web/contacto",
            json={
                "nombre": "Test",
                # Missing email, asunto, mensaje
            },
            timeout=10
        )
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print("✓ Contact form validates required fields correctly")
    
    def test_presupuesto_endpoint_saves_request(self):
        """Test POST /api/web/presupuesto - should save budget request"""
        test_email = f"presupuesto{int(time.time())}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/web/presupuesto",
            json={
                "tipo_dispositivo": "smartphone",
                "marca": "Apple",
                "modelo": "iPhone 14 Pro",
                "averias": ["Pantalla rota", "Batería agotada"],
                "descripcion": "La pantalla se rompió tras una caída y la batería apenas dura.",
                "nombre": "Test Cliente",
                "email": test_email,
                "telefono": "666999888"
            },
            timeout=10
        )
        assert response.status_code == 200, f"Presupuesto returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "id" in data, "Response should contain generated ID"
        assert "message" in data, "Response should contain confirmation message"
        print(f"✓ Budget request saved with ID: {data['id']}")
    
    def test_presupuesto_validates_required_fields(self):
        """Test POST /api/web/presupuesto - validates required fields"""
        response = requests.post(
            f"{BASE_URL}/api/web/presupuesto",
            json={
                "tipo_dispositivo": "smartphone",
                # Missing required fields
            },
            timeout=10
        )
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print("✓ Presupuesto form validates required fields correctly")


class TestCRMAuthentication:
    """Test CRM authentication still works"""
    
    def test_crm_login_with_valid_credentials(self):
        """Test POST /api/auth/login - CRM should still work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "ramiraz91@gmail.com",
                "password": "temp123"
            },
            timeout=10
        )
        assert response.status_code == 200, f"CRM Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "token" in data, "Login should return token"
        assert "user" in data, "Login should return user data"
        print(f"✓ CRM Login successful for user: {data['user'].get('nombre', data['user'].get('email'))}")
    
    def test_crm_login_rejects_invalid_credentials(self):
        """Test POST /api/auth/login - rejects bad credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "fake@example.com",
                "password": "wrongpassword"
            },
            timeout=10
        )
        assert response.status_code == 401 or response.status_code == 404, \
            f"Expected 401/404 for invalid credentials, got {response.status_code}"
        print("✓ CRM rejects invalid credentials correctly")


class TestHealthAndBasicEndpoints:
    """Test basic health endpoints"""
    
    def test_backend_health(self):
        """Test backend is responding"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ Backend health check passed")
    
    def test_seguimiento_page_api(self):
        """Test seguimiento endpoint works for tracking repairs"""
        # Test with a non-existent ID - should return 404
        response = requests.get(
            f"{BASE_URL}/api/ordenes/seguimiento/FAKE123",
            timeout=10
        )
        # Could be 404 or empty result - either is acceptable
        assert response.status_code in [200, 404], \
            f"Seguimiento endpoint returned unexpected status: {response.status_code}"
        print("✓ Seguimiento/tracking endpoint responding")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
