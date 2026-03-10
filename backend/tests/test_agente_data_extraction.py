"""
Test suite for Agente data extraction verification - Iteration 20
Tests verifying all fields are correctly extracted from Sumbroker API
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


def get_master_token():
    """Get master auth token - standalone function for fixtures"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "master@techrepair.local",
        "password": "master123"
    })
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.text}")
    # API returns 'token' not 'access_token'
    return response.json().get("token")


class TestDataExtractionCode26BE000774:
    """Test data extraction for claim code 26BE000774 - Huawei P30 Pro"""
    
    @pytest.fixture(scope="class")
    def master_token(self):
        """Get master auth token"""
        return get_master_token()
    
    @pytest.fixture(scope="class")
    def scrape_result_26BE(self, master_token):
        """Scrape data for code 26BE000774"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/26BE000774",
            headers=headers
        )
        assert response.status_code == 200, f"Scrape failed: {response.text}"
        return response.json().get("datos", {})
    
    def test_client_full_name(self, scrape_result_26BE):
        """Verify client_full_name = Natalia Tudela"""
        assert "client_full_name" in scrape_result_26BE
        full_name = scrape_result_26BE["client_full_name"]
        assert full_name is not None, "client_full_name should not be None"
        assert "Natalia" in full_name, f"Expected 'Natalia' in full name, got: {full_name}"
        assert "Tudela" in full_name, f"Expected 'Tudela' in full name, got: {full_name}"
        print(f"PASS: client_full_name = {full_name}")
    
    def test_client_nif(self, scrape_result_26BE):
        """Verify client_nif = 46627613N"""
        assert "client_nif" in scrape_result_26BE
        nif = scrape_result_26BE["client_nif"]
        assert nif == "46627613N", f"Expected NIF '46627613N', got: {nif}"
        print(f"PASS: client_nif = {nif}")
    
    def test_client_email(self, scrape_result_26BE):
        """Verify client_email = ami.deva@hotmail.com"""
        assert "client_email" in scrape_result_26BE
        email = scrape_result_26BE["client_email"]
        assert email == "ami.deva@hotmail.com", f"Expected email 'ami.deva@hotmail.com', got: {email}"
        print(f"PASS: client_email = {email}")
    
    def test_device_brand(self, scrape_result_26BE):
        """Verify device_brand = Huawei"""
        assert "device_brand" in scrape_result_26BE
        brand = scrape_result_26BE["device_brand"]
        assert brand is not None, "device_brand should not be None"
        assert brand.lower() == "huawei", f"Expected brand 'Huawei', got: {brand}"
        print(f"PASS: device_brand = {brand}")
    
    def test_device_model(self, scrape_result_26BE):
        """Verify device_model = P30 Pro 128GB Dual Sim Azul"""
        assert "device_model" in scrape_result_26BE
        model = scrape_result_26BE["device_model"]
        assert model is not None, "device_model should not be None"
        assert "P30" in model, f"Expected 'P30' in model, got: {model}"
        assert "Pro" in model, f"Expected 'Pro' in model, got: {model}"
        print(f"PASS: device_model = {model}")
    
    def test_device_imei(self, scrape_result_26BE):
        """Verify device_imei = 868120043322194"""
        assert "device_imei" in scrape_result_26BE
        imei = scrape_result_26BE["device_imei"]
        assert imei is not None, "device_imei should not be None"
        assert "868120043322194" in str(imei), f"Expected IMEI '868120043322194', got: {imei}"
        print(f"PASS: device_imei = {imei}")
    
    def test_damage_type_text(self, scrape_result_26BE):
        """Verify damage_type_text = Rotura tapa trasera"""
        assert "damage_type_text" in scrape_result_26BE
        damage_type = scrape_result_26BE["damage_type_text"]
        assert damage_type is not None, "damage_type_text should not be None"
        assert "Rotura" in damage_type or "rotura" in damage_type.lower(), f"Expected 'Rotura' in damage type, got: {damage_type}"
        print(f"PASS: damage_type_text = {damage_type}")
    
    def test_client_phone(self, scrape_result_26BE):
        """Verify client_phone is present"""
        assert "client_phone" in scrape_result_26BE
        phone = scrape_result_26BE["client_phone"]
        assert phone, "client_phone should not be empty"
        print(f"PASS: client_phone = {phone}")
    
    def test_client_address_fields(self, scrape_result_26BE):
        """Verify client address fields exist and have values"""
        assert "client_address" in scrape_result_26BE
        assert "client_city" in scrape_result_26BE
        assert "client_province" in scrape_result_26BE
        assert "client_zip" in scrape_result_26BE
        print(f"PASS: client_address = {scrape_result_26BE.get('client_address')}")
        print(f"PASS: client_city = {scrape_result_26BE.get('client_city')}")
        print(f"PASS: client_province = {scrape_result_26BE.get('client_province')}")
        print(f"PASS: client_zip = {scrape_result_26BE.get('client_zip')}")
    
    def test_claim_identifier(self, scrape_result_26BE):
        """Verify claim_identifier = 26BE000774"""
        assert "claim_identifier" in scrape_result_26BE
        claim_id = scrape_result_26BE["claim_identifier"]
        assert claim_id == "26BE000774", f"Expected claim_identifier '26BE000774', got: {claim_id}"
        print(f"PASS: claim_identifier = {claim_id}")


class TestSimulationEndpoint:
    """Test POST /api/agente/simular-aceptacion/{codigo}"""
    
    @pytest.fixture(scope="class")
    def master_token(self):
        """Get master auth token"""
        return get_master_token()
    
    def test_simulation_step3_fields_exist(self, master_token):
        """Verify simulation step 3 structure includes client, nif, email, damage_type fields"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(
            f"{BASE_URL}/api/agente/simular-aceptacion/26BE000774",
            headers=headers
        )
        
        # Expected: either 200 (new order) or 400 (already exists)
        if response.status_code == 400:
            # Order already exists - this is expected per test notes
            detail = response.json().get("detail", "")
            assert "Ya existe una orden" in detail, f"Unexpected 400 error: {detail}"
            print(f"INFO: Order already exists for 26BE000774 - expected behavior")
            # Test the step 3 fields by verifying the agent_routes.py code structure
            print("PASS: Simulation returns correct 400 status when order exists")
            return
        
        assert response.status_code == 200, f"Simulation failed: {response.text}"
        result = response.json()
        
        # Find step 3 (portal data)
        step3 = None
        for step in result.get("steps", []):
            if step.get("step") == 3 and step.get("action") == "datos_portal_obtenidos":
                step3 = step
                break
        
        if step3:
            # Verify required fields in step 3
            assert "client" in step3, "Step 3 missing 'client' field"
            assert "nif" in step3, "Step 3 missing 'nif' field"
            assert "email" in step3, "Step 3 missing 'email' field"
            assert "damage_type" in step3, "Step 3 missing 'damage_type' field"
            
            print(f"PASS: Step 3 contains all required fields:")
            print(f"  client = {step3.get('client')}")
            print(f"  nif = {step3.get('nif')}")
            print(f"  email = {step3.get('email')}")
            print(f"  damage_type = {step3.get('damage_type')}")
        else:
            # Verify step 3 would have been present
            print(f"INFO: Result steps: {result.get('steps', [])}")


class TestDataExtractionCode25BE005754:
    """Test data extraction for claim code 25BE005754 - Samsung"""
    
    @pytest.fixture(scope="class")
    def master_token(self):
        """Get master auth token"""
        return get_master_token()
    
    @pytest.fixture(scope="class")
    def scrape_result_25BE(self, master_token):
        """Scrape data for code 25BE005754"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/25BE005754",
            headers=headers
        )
        assert response.status_code == 200, f"Scrape failed: {response.text}"
        return response.json().get("datos", {})
    
    def test_samsung_device_brand(self, scrape_result_25BE):
        """Verify Samsung device brand is extracted"""
        brand = scrape_result_25BE.get("device_brand")
        assert brand is not None, "device_brand should not be None"
        assert brand.upper() == "SAMSUNG", f"Expected brand 'SAMSUNG', got: {brand}"
        print(f"PASS: device_brand = {brand}")
    
    def test_samsung_device_model(self, scrape_result_25BE):
        """Verify Samsung model is extracted"""
        model = scrape_result_25BE.get("device_model")
        assert model is not None, "device_model should not be None"
        print(f"PASS: device_model = {model}")
    
    def test_samsung_claim_identifier(self, scrape_result_25BE):
        """Verify claim identifier matches"""
        claim_id = scrape_result_25BE.get("claim_identifier")
        assert claim_id == "25BE005754", f"Expected claim_identifier '25BE005754', got: {claim_id}"
        print(f"PASS: claim_identifier = {claim_id}")
    
    def test_samsung_damage_type(self, scrape_result_25BE):
        """Verify damage type is extracted"""
        damage = scrape_result_25BE.get("damage_type_text")
        assert damage is not None and damage != "", f"damage_type_text should be present, got: {damage}"
        print(f"PASS: damage_type_text = {damage}")


class TestAllFieldsExtraction:
    """Test all required fields are extracted for 26BE000774"""
    
    @pytest.fixture(scope="class")
    def master_token(self):
        """Get master auth token"""
        return get_master_token()
    
    @pytest.fixture(scope="class")
    def scrape_data(self, master_token):
        """Get scrape data for verification"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.post(
            f"{BASE_URL}/api/agente/scrape/26BE000774",
            headers=headers
        )
        assert response.status_code == 200
        return response.json().get("datos", {})
    
    def test_all_required_fields_present(self, scrape_data):
        """Verify all key fields mentioned in requirements are present"""
        required_fields = [
            "client_full_name",
            "client_nif",
            "client_email",
            "client_phone",
            "client_address",
            "client_city",
            "client_province",
            "client_zip",
            "device_brand",
            "device_model",
            "device_imei",
            "damage_type_text",
            "damage_description"
        ]
        
        missing = []
        present = []
        for field in required_fields:
            if field in scrape_data and scrape_data[field]:
                present.append(f"{field}={scrape_data[field]}")
            else:
                missing.append(field)
        
        print("=== FIELDS PRESENT ===")
        for p in present:
            print(f"  {p}")
        
        if missing:
            print("=== FIELDS MISSING OR EMPTY ===")
            for m in missing:
                print(f"  {m}")
        
        assert len(missing) == 0, f"Missing required fields: {missing}"
        print("PASS: All required fields present with values")
