"""
Test Brother Print Agent endpoints
- GET /api/print/agent/status - Agent info
- GET /api/print/agent/download - Agent ZIP download
"""
import pytest
import requests
import os
import zipfile
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPrintAgentEndpoints:
    """Tests for Brother QL-800 print agent endpoints"""
    
    def test_agent_status_returns_correct_info(self):
        """Test /api/print/agent/status returns version, label_format, download_url"""
        response = requests.get(f"{BASE_URL}/api/print/agent/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "version" in data
        assert data["version"] == "1.0.0"
        
        assert "label_format" in data
        assert data["label_format"] == "DK-11204"
        
        assert "label_size" in data
        assert data["label_size"] == "17mm x 54mm"
        
        assert "printer" in data
        assert data["printer"] == "Brother QL-800"
        
        assert "agent_port" in data
        assert data["agent_port"] == 5555
        
        assert "download_url" in data
        assert data["download_url"] == "/api/print/agent/download"
    
    def test_agent_download_returns_valid_zip(self):
        """Test /api/print/agent/download returns a valid ZIP file"""
        response = requests.get(f"{BASE_URL}/api/print/agent/download")
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/zip'
        
        # Verify it's a valid ZIP
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            file_list = zf.namelist()
            
            # Should have 8 files
            assert len(file_list) == 8, f"Expected 8 files, got {len(file_list)}: {file_list}"
            
            # Verify expected files are present
            expected_files = [
                "brother-label-agent/agent.py",
                "brother-label-agent/label_generator.py",
                "brother-label-agent/printer_service.py",
                "brother-label-agent/config.json",
                "brother-label-agent/requirements.txt",
                "brother-label-agent/install.bat",
                "brother-label-agent/start.bat",
                "brother-label-agent/README.md",
            ]
            
            for expected in expected_files:
                assert expected in file_list, f"Missing file: {expected}"
    
    def test_agent_download_zip_content_not_empty(self):
        """Test that ZIP files have actual content"""
        response = requests.get(f"{BASE_URL}/api/print/agent/download")
        
        assert response.status_code == 200
        
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            # Check that agent.py has content
            agent_info = zf.getinfo("brother-label-agent/agent.py")
            assert agent_info.file_size > 1000, "agent.py should have substantial content"
            
            # Check that label_generator.py has content
            label_info = zf.getinfo("brother-label-agent/label_generator.py")
            assert label_info.file_size > 1000, "label_generator.py should have substantial content"


class TestLabelImageDimensions:
    """Test that generated label images have correct dimensions for DK-11204"""
    
    def test_preview_images_exist(self):
        """Test that preview images were generated"""
        agent_dir = "/app/brother-label-agent"
        
        assert os.path.exists(f"{agent_dir}/preview_ot_label.png"), "OT label preview missing"
        assert os.path.exists(f"{agent_dir}/preview_inv_label.png"), "Inventory label preview missing"
    
    def test_label_dimensions_dk11204(self):
        """Test that labels are 638x201 pixels (DK-11204 at 300 DPI)"""
        from PIL import Image
        
        agent_dir = "/app/brother-label-agent"
        
        # OT Label
        ot_img = Image.open(f"{agent_dir}/preview_ot_label.png")
        assert ot_img.size == (638, 201), f"OT label should be 638x201, got {ot_img.size}"
        
        # Inventory Label
        inv_img = Image.open(f"{agent_dir}/preview_inv_label.png")
        assert inv_img.size == (638, 201), f"Inventory label should be 638x201, got {inv_img.size}"
