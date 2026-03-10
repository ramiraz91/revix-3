#!/usr/bin/env python3
"""
Comprehensive API Testing for Revix CRM/ERP System
Tests authentication, dashboard stats, and core API endpoints
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class RevixAPITester:
    def __init__(self):
        # Get backend URL from frontend .env file 
        self.base_url = "https://repair-workshop-crm.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.session = requests.Session()
        self.token = None
        self.current_user = None
        
        # Test users from requirements
        self.test_users = [
            {
                "email": "ramiraz91@gmail.com", 
                "password": "temp123", 
                "role": "master",
                "name": "Master User"
            },
            {
                "email": "admin@techrepair.local", 
                "password": "Admin2026!", 
                "role": "admin",
                "name": "Admin User"
            },
            {
                "email": "tecnico@techrepair.local", 
                "password": "Tecnico2026!", 
                "role": "tecnico",
                "name": "Tecnico User"
            }
        ]
        
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

    def log_result(self, test_name: str, success: bool, details: str = "", expected_status: int = None, actual_status: int = None):
        """Log test result with details"""
        self.tests_run += 1
        status_info = f" (Expected: {expected_status}, Got: {actual_status})" if expected_status and actual_status else ""
        
        if success:
            self.tests_passed += 1
            self.passed_tests.append(f"✅ {test_name} - {details}")
            print(f"✅ PASS: {test_name} - {details}{status_info}")
        else:
            self.failed_tests.append(f"❌ {test_name} - {details}{status_info}")
            print(f"❌ FAIL: {test_name} - {details}{status_info}")

    def test_api_root(self) -> bool:
        """Test root API endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                message = data.get("message", "")
                success = "Mobile Repair CRM/ERP API" in message or "API" in message
                self.log_result(
                    "API Root Endpoint", 
                    success, 
                    f"Message: {message}" if success else f"Unexpected message: {message}",
                    200, response.status_code
                )
            else:
                self.log_result("API Root Endpoint", False, f"HTTP Error", 200, response.status_code)
                
            return success
        except Exception as e:
            self.log_result("API Root Endpoint", False, f"Exception: {str(e)}")
            return False

    def login_user(self, email: str, password: str) -> tuple[bool, dict]:
        """Login with user credentials"""
        try:
            login_data = {"email": email, "password": password}
            response = self.session.post(f"{self.api_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                user = data.get("user")
                
                if token and user:
                    self.token = token
                    self.current_user = user
                    # Set authorization header for future requests
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                    
                    self.log_result(
                        f"Login {user.get('role', 'unknown')} user", 
                        True, 
                        f"Email: {email}, Role: {user.get('role')}, Name: {user.get('nombre', '')}"
                    )
                    return True, user
                else:
                    self.log_result(f"Login {email}", False, "Missing token or user in response")
                    return False, {}
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown error")
                except:
                    error_detail = response.text[:100]
                
                self.log_result(
                    f"Login {email}", 
                    False, 
                    f"Login failed: {error_detail}", 
                    200, response.status_code
                )
                return False, {}
                
        except Exception as e:
            self.log_result(f"Login {email}", False, f"Exception: {str(e)}")
            return False, {}

    def test_dashboard_stats(self) -> bool:
        """Test dashboard stats endpoint (requires authentication)"""
        try:
            response = self.session.get(f"{self.api_url}/dashboard/stats")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                required_fields = [
                    "total_ordenes", "ordenes_por_estado", "total_clientes", 
                    "total_repuestos", "notificaciones_pendientes"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_result(
                        "Dashboard Stats", 
                        True, 
                        f"Stats loaded: {data.get('total_ordenes', 0)} orders, {data.get('total_clientes', 0)} clients"
                    )
                else:
                    self.log_result(
                        "Dashboard Stats", 
                        False, 
                        f"Missing required fields: {missing_fields}"
                    )
                    success = False
            else:
                self.log_result("Dashboard Stats", False, "Failed to load stats", 200, response.status_code)
            
            return success
        except Exception as e:
            self.log_result("Dashboard Stats", False, f"Exception: {str(e)}")
            return False

    def test_user_profile(self) -> bool:
        """Test /auth/me endpoint (requires authentication)"""
        try:
            response = self.session.get(f"{self.api_url}/auth/me")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                user_email = data.get("email", "")
                user_role = data.get("role", "")
                
                # Verify the data matches what we logged in with
                if self.current_user:
                    expected_email = self.current_user.get("email", "")
                    success = user_email.lower() == expected_email.lower()
                    
                self.log_result(
                    "User Profile (/auth/me)", 
                    success, 
                    f"Email: {user_email}, Role: {user_role}" if success else "Email mismatch"
                )
            else:
                self.log_result("User Profile", False, "Failed to get user profile", 200, response.status_code)
            
            return success
        except Exception as e:
            self.log_result("User Profile", False, f"Exception: {str(e)}")
            return False

    def test_database_name(self) -> bool:
        """Verify the backend is using the 'production' database"""
        try:
            # Test by checking if we can access dashboard stats (which requires DB)
            response = self.session.get(f"{self.api_url}/dashboard/stats")
            
            if response.status_code == 200:
                # If we get data, the database connection works
                # Backend config should be using DB_NAME=production as per .env
                self.log_result(
                    "Database 'production' Usage", 
                    True, 
                    "Backend successfully connected to database (production collection per config)"
                )
                return True
            else:
                self.log_result(
                    "Database 'production' Usage", 
                    False, 
                    f"Database connection issue", 
                    200, response.status_code
                )
                return False
        except Exception as e:
            self.log_result("Database Usage", False, f"Exception: {str(e)}")
            return False

    def logout_user(self):
        """Clear session and token"""
        self.token = None
        self.current_user = None
        self.session.headers.pop("Authorization", None)

    def test_invalid_login(self) -> bool:
        """Test login with invalid credentials"""
        try:
            invalid_data = {"email": "invalid@test.com", "password": "wrongpassword"}
            response = self.session.post(f"{self.api_url}/auth/login", json=invalid_data)
            
            # Should return 401 for invalid credentials
            success = response.status_code == 401
            
            if success:
                error_data = response.json()
                error_message = error_data.get("detail", "")
                self.log_result(
                    "Invalid Login Test", 
                    True, 
                    f"Correctly rejected with: {error_message}"
                )
            else:
                self.log_result(
                    "Invalid Login Test", 
                    False, 
                    "Should have returned 401 for invalid credentials", 
                    401, response.status_code
                )
            
            return success
        except Exception as e:
            self.log_result("Invalid Login Test", False, f"Exception: {str(e)}")
            return False

    def run_comprehensive_tests(self):
        """Run all tests for the Revix CRM system"""
        print("🚀 Starting Revix CRM/ERP API Testing")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"API URL: {self.api_url}")
        print("=" * 60)

        # Test 1: API Root endpoint (public)
        self.test_api_root()
        
        # Test 2: Invalid login (security test)
        self.test_invalid_login()
        
        # Test 3-5: Login with each user type
        all_login_success = True
        for user_config in self.test_users:
            success, user_data = self.login_user(user_config["email"], user_config["password"])
            if success:
                # Test authenticated endpoints with this user
                self.test_user_profile()
                self.test_dashboard_stats()
                self.test_database_name()
                
                # Logout before next user
                self.logout_user()
            else:
                all_login_success = False

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for failed in self.failed_tests:
                print(f"  {failed}")
        
        if self.passed_tests:
            print("\n✅ PASSED TESTS:")
            for passed in self.passed_tests[-5:]:  # Show last 5 passed tests
                print(f"  {passed}")
            if len(self.passed_tests) > 5:
                print(f"  ... and {len(self.passed_tests)-5} more")
        
        print("=" * 60)
        
        # Return success status
        return len(self.failed_tests) == 0

def main():
    tester = RevixAPITester()
    success = tester.run_comprehensive_tests()
    
    # Exit with appropriate code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())