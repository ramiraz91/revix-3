"""
Iteration 38: Security Features Testing
- Login error messages
- Rate limiting (5 failed attempts = 429)
- Password recovery flow (POST /api/auth/recuperar-password)
- Token verification (GET /api/auth/verificar-token-reset)
- Password reset (POST /api/auth/reset-password)
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ramiraz91@gmail.com"
TEST_PASSWORD = "temp123"
INVALID_EMAIL = f"nonexistent_{uuid.uuid4().hex[:8]}@test.com"
INVALID_PASSWORD = "wrongpassword123"


class TestLoginErrorMessages:
    """Test that login shows specific error messages"""
    
    def test_login_invalid_credentials_shows_error(self):
        """Login with wrong password should return 401 with specific message"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": INVALID_PASSWORD}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field"
        # Should contain error message in Spanish
        assert "incorrecto" in data["detail"].lower() or "contraseña" in data["detail"].lower(), \
            f"Error message should mention incorrect credentials: {data['detail']}"
        print(f"✓ Login error message: {data['detail']}")
    
    def test_login_nonexistent_email_shows_error(self):
        """Login with non-existent email should return 401 with specific message"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": INVALID_EMAIL, "password": INVALID_PASSWORD}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field"
        print(f"✓ Non-existent email error: {data['detail']}")
    
    def test_login_valid_credentials_success(self):
        """Login with valid credentials should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user info"
        print(f"✓ Valid login successful for {data['user']['email']}")


class TestRateLimiting:
    """Test rate limiting on login endpoint"""
    
    def test_rate_limit_after_failed_attempts(self):
        """After 5 failed attempts, should return 429"""
        # Use a unique email to avoid affecting other tests
        unique_email = f"ratelimit_test_{uuid.uuid4().hex[:8]}@test.com"
        
        # Make 5 failed login attempts
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": unique_email, "password": "wrongpass"}
            )
            print(f"Attempt {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                print(f"✓ Rate limit triggered at attempt {i+1}")
                data = response.json()
                assert "detail" in data
                assert "espera" in data["detail"].lower() or "demasiados" in data["detail"].lower(), \
                    f"Rate limit message should mention waiting: {data['detail']}"
                return  # Test passed
        
        # 6th attempt should definitely be rate limited
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "wrongpass"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 failed attempts, got {response.status_code}"
        data = response.json()
        print(f"✓ Rate limit message: {data.get('detail', 'No detail')}")


class TestPasswordRecovery:
    """Test password recovery endpoints"""
    
    def test_recuperar_password_endpoint_exists(self):
        """POST /api/auth/recuperar-password should respond"""
        response = requests.post(
            f"{BASE_URL}/api/auth/recuperar-password",
            json={"email": TEST_EMAIL}
        )
        # Should return 200 regardless of whether email exists (security)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        print(f"✓ Recovery endpoint response: {data['message']}")
    
    def test_recuperar_password_nonexistent_email(self):
        """Recovery for non-existent email should still return 200 (security)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/recuperar-password",
            json={"email": f"nonexistent_{uuid.uuid4().hex}@test.com"}
        )
        # Should return same response to not reveal if email exists
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data
        print(f"✓ Non-existent email recovery (same response): {data['message']}")
    
    def test_verificar_token_reset_invalid_token(self):
        """GET /api/auth/verificar-token-reset with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/verificar-token-reset",
            params={"token": "invalid_token_12345"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "valido" in data, "Response should contain 'valido' field"
        assert data["valido"] == False, "Invalid token should return valido=False"
        assert "motivo" in data, "Invalid token should include reason"
        print(f"✓ Invalid token verification: valido={data['valido']}, motivo={data.get('motivo')}")
    
    def test_reset_password_invalid_token(self):
        """POST /api/auth/reset-password with invalid token should fail"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": "invalid_token_12345", "nueva_password": "newpass123"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid token reset error: {data['detail']}")
    
    def test_reset_password_short_password(self):
        """Reset with password < 6 chars should fail"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": "any_token", "nueva_password": "12345"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "6" in data["detail"] or "caracteres" in data["detail"].lower(), \
            f"Should mention minimum 6 characters: {data['detail']}"
        print(f"✓ Short password validation: {data['detail']}")


class TestEndpointAvailability:
    """Verify all security endpoints are available"""
    
    def test_login_endpoint_available(self):
        """POST /api/auth/login should be available"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@test.com", "password": "test"}
        )
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Login endpoint not available: {response.status_code}"
        print(f"✓ Login endpoint available (status: {response.status_code})")
    
    def test_recuperar_password_endpoint_available(self):
        """POST /api/auth/recuperar-password should be available"""
        response = requests.post(
            f"{BASE_URL}/api/auth/recuperar-password",
            json={"email": "test@test.com"}
        )
        assert response.status_code not in [404, 405], f"Recovery endpoint not available: {response.status_code}"
        print(f"✓ Recovery endpoint available (status: {response.status_code})")
    
    def test_verificar_token_endpoint_available(self):
        """GET /api/auth/verificar-token-reset should be available"""
        response = requests.get(
            f"{BASE_URL}/api/auth/verificar-token-reset",
            params={"token": "test"}
        )
        assert response.status_code not in [404, 405], f"Token verify endpoint not available: {response.status_code}"
        print(f"✓ Token verify endpoint available (status: {response.status_code})")
    
    def test_reset_password_endpoint_available(self):
        """POST /api/auth/reset-password should be available"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"token": "test", "nueva_password": "testpass"}
        )
        assert response.status_code not in [404, 405], f"Reset endpoint not available: {response.status_code}"
        print(f"✓ Reset endpoint available (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
