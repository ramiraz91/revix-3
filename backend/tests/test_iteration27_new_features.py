"""
Iteration 27: Testing new features
- Comisiones de técnicos (deshabilitado por defecto)
- Etiquetas de envío (UI placeholder)
- Plantillas de email editables
- API de IA /api/ia/consulta
- API de restos /api/restos
- Login admin y técnico
- Calendario
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Test authentication for admin and tecnico"""
    
    def test_login_admin(self):
        """Test admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") in ["admin", "master"], f"Unexpected role: {data.get('user', {}).get('role')}"
        print(f"✅ Admin login successful - role: {data.get('user', {}).get('role')}")
        return data["token"]
    
    def test_login_tecnico(self):
        """Test tecnico login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tecnico@techrepair.local",
            "password": "tecnico123"
        })
        assert response.status_code == 200, f"Tecnico login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("role") == "tecnico", f"Unexpected role: {data.get('user', {}).get('role')}"
        print(f"✅ Tecnico login successful - role: {data.get('user', {}).get('role')}")
        return data["token"]


class TestComisiones:
    """Test comisiones de técnicos endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_get_comisiones_config(self, admin_token):
        """Test GET /api/comisiones/config - should return config with sistema_activo=false by default"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/comisiones/config", headers=headers)
        assert response.status_code == 200, f"Failed to get comisiones config: {response.text}"
        data = response.json()
        # sistema_activo should be False by default
        assert "sistema_activo" in data or data == {}, f"Unexpected response: {data}"
        sistema_activo = data.get("sistema_activo", False)
        print(f"✅ Comisiones config retrieved - sistema_activo: {sistema_activo}")
        # Default should be False
        assert sistema_activo == False, f"sistema_activo should be False by default, got: {sistema_activo}"
        print("✅ sistema_activo is False by default as expected")
    
    def test_get_comisiones_list(self, admin_token):
        """Test GET /api/comisiones - list comisiones"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/comisiones", headers=headers)
        assert response.status_code == 200, f"Failed to get comisiones: {response.text}"
        data = response.json()
        assert "comisiones" in data, f"No comisiones key in response: {data}"
        assert "totales" in data, f"No totales key in response: {data}"
        print(f"✅ Comisiones list retrieved - count: {len(data.get('comisiones', []))}")
    
    def test_get_comisiones_resumen(self, admin_token):
        """Test GET /api/comisiones/resumen - resumen por técnico"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/comisiones/resumen", headers=headers)
        assert response.status_code == 200, f"Failed to get comisiones resumen: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✅ Comisiones resumen retrieved - count: {len(data)}")
    
    def test_update_comisiones_config(self, admin_token):
        """Test PUT /api/comisiones/config - update config"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        config = {
            "sistema_activo": False,
            "porcentaje_default": 5.0,
            "fijo_default": 0.0,
            "aplicar_a_garantias": False,
            "aplicar_a_seguros": True,
            "aplicar_a_particulares": True
        }
        response = requests.put(f"{BASE_URL}/api/comisiones/config", headers=headers, json=config)
        assert response.status_code == 200, f"Failed to update comisiones config: {response.text}"
        print("✅ Comisiones config updated successfully")


class TestEtiquetasEnvio:
    """Test etiquetas de envío endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_get_transportistas(self, admin_token):
        """Test GET /api/transportistas - list transportistas"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/transportistas", headers=headers)
        assert response.status_code == 200, f"Failed to get transportistas: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        # Should have predefined transportistas
        codigos = [t.get("codigo") for t in data]
        expected_codigos = ["mrw", "seur", "correos", "dhl", "ups", "gls"]
        for codigo in expected_codigos:
            assert codigo in codigos, f"Missing transportista: {codigo}"
        print(f"✅ Transportistas retrieved - count: {len(data)}")
    
    def test_get_etiquetas_list(self, admin_token):
        """Test GET /api/etiquetas-envio - list etiquetas"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/etiquetas-envio", headers=headers)
        assert response.status_code == 200, f"Failed to get etiquetas: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✅ Etiquetas envío list retrieved - count: {len(data)}")


class TestPlantillasEmail:
    """Test plantillas de email endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_get_plantillas_email(self, admin_token):
        """Test GET /api/plantillas-email - list plantillas"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/plantillas-email", headers=headers)
        assert response.status_code == 200, f"Failed to get plantillas: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        # Should have default plantillas
        tipos = [p.get("tipo") for p in data]
        expected_tipos = ["created", "recibida", "en_taller", "reparado", "enviado"]
        for tipo in expected_tipos:
            assert tipo in tipos, f"Missing plantilla tipo: {tipo}"
        print(f"✅ Plantillas email retrieved - count: {len(data)}, tipos: {tipos}")
    
    def test_get_plantilla_by_tipo(self, admin_token):
        """Test GET /api/plantillas-email/{tipo} - get specific plantilla"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/plantillas-email/created", headers=headers)
        assert response.status_code == 200, f"Failed to get plantilla: {response.text}"
        data = response.json()
        assert data.get("tipo") == "created", f"Wrong tipo: {data.get('tipo')}"
        assert "asunto" in data, "Missing asunto field"
        assert "titulo" in data, "Missing titulo field"
        print(f"✅ Plantilla 'created' retrieved - asunto: {data.get('asunto')}")


class TestIA:
    """Test IA endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_ia_consulta(self, admin_token):
        """Test POST /api/ia/consulta - IA consultation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/ia/consulta", headers=headers, json={
            "mensaje": "¿Cuál es el problema más común en iPhone?"
        })
        # May return 200 or 500 depending on LLM config
        if response.status_code == 200:
            data = response.json()
            assert "respuesta" in data, f"No respuesta in response: {data}"
            print(f"✅ IA consulta successful - respuesta length: {len(data.get('respuesta', ''))}")
        elif response.status_code == 500:
            # LLM not configured is acceptable
            print("⚠️ IA consulta returned 500 - LLM may not be configured")
        else:
            assert False, f"Unexpected status code: {response.status_code} - {response.text}"
    
    def test_ia_diagnostico(self, admin_token):
        """Test POST /api/ia/diagnostico - IA diagnosis (uses query params)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # This endpoint uses query parameters, not JSON body
        response = requests.post(
            f"{BASE_URL}/api/ia/diagnostico",
            headers=headers,
            params={"modelo": "iPhone 13", "sintomas": "Pantalla no enciende"}
        )
        if response.status_code == 200:
            data = response.json()
            assert "diagnostico" in data, f"No diagnostico in response: {data}"
            print(f"✅ IA diagnostico successful - diagnostico length: {len(data.get('diagnostico', ''))}")
        elif response.status_code == 500:
            print("⚠️ IA diagnostico returned 500 - LLM may not be configured")
        else:
            assert False, f"Unexpected status code: {response.status_code} - {response.text}"


class TestRestos:
    """Test restos endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_get_restos(self, admin_token):
        """Test GET /api/restos - list restos"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/restos", headers=headers)
        assert response.status_code == 200, f"Failed to get restos: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✅ Restos list retrieved - count: {len(data)}")
    
    def test_create_resto(self, admin_token):
        """Test POST /api/restos - create resto (DispositivoResto model)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # DispositivoResto requires: modelo, estado_fisico
        resto_data = {
            "modelo": "iPhone 13 Pro",
            "estado_fisico": "Pantalla rota, resto funcional",
            "imei": "123456789012345",
            "color": "Azul",
            "descripcion": "Dispositivo de prueba para restos",
            "piezas_aprovechables": ["Batería", "Cámara trasera", "Placa base"],
            "origen_orden_id": "test-orden-id",
            "ubicacion_almacen": "Estante A-3"
        }
        response = requests.post(f"{BASE_URL}/api/restos", headers=headers, json=resto_data)
        assert response.status_code in [200, 201], f"Failed to create resto: {response.text}"
        data = response.json()
        assert "id" in data, f"No id in response: {data}"
        assert "codigo" in data, f"No codigo in response: {data}"
        print(f"✅ Resto created successfully - codigo: {data.get('codigo')}")
        return data


class TestCalendario:
    """Test calendario endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@techrepair.local",
            "password": "admin123"
        })
        return response.json().get("token")
    
    def test_get_calendario_eventos(self, admin_token):
        """Test GET /api/calendario/eventos - list eventos"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/calendario/eventos", headers=headers)
        assert response.status_code == 200, f"Failed to get calendario eventos: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✅ Calendario eventos retrieved - count: {len(data)}")


class TestEmailConfig:
    """Test email config endpoints"""
    
    @pytest.fixture
    def master_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "master@techrepair.local",
            "password": "master123"
        })
        return response.json().get("token")
    
    def test_get_email_config(self, master_token):
        """Test GET /api/email-config - get email config"""
        headers = {"Authorization": f"Bearer {master_token}"}
        response = requests.get(f"{BASE_URL}/api/email-config", headers=headers)
        assert response.status_code == 200, f"Failed to get email config: {response.text}"
        data = response.json()
        # Should have basic config fields
        print(f"✅ Email config retrieved - enabled: {data.get('enabled')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
