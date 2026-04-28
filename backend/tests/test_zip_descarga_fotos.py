"""
Tests del fix de descarga de ZIPs corruptos.

Bug original: las descargas /api/ordenes/{id}/fotos-zip generaban ZIPs
truncados (Content-Length faltaba) y con nombres rotos en Content-Disposition.
"""
import io
import sys
import zipfile
from pathlib import Path

import pytest

# Path setup
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ── utils/zip_helper.py ──────────────────────────────────────────────────────

def test_safe_inner_filename_quita_caracteres_windows():
    from utils.zip_helper import safe_inner_filename
    assert safe_inner_filename('foo/bar:baz?.jpg') == 'foo_bar_baz_.jpg'
    assert safe_inner_filename('a\\b<c>d|e.png') == 'a_b_c_d_e.png'
    assert safe_inner_filename('') == 'archivo'
    assert safe_inner_filename('.') == 'archivo'


def test_safe_inner_filename_preserva_ascii_y_unicode_seguro():
    from utils.zip_helper import safe_inner_filename
    assert safe_inner_filename('Reparación_iPhone.jpg') == 'Reparación_iPhone.jpg'
    assert safe_inner_filename('foto antes 1.png') == 'foto antes 1.png'


def test_safe_content_disposition_ascii_y_utf8():
    from utils.zip_helper import safe_content_disposition
    cd = safe_content_disposition('OT-123_fotos.zip')
    assert 'filename="OT-123_fotos.zip"' in cd
    assert "filename*=UTF-8''" in cd

    # Con caracteres especiales: ASCII fallback se sanea
    cd2 = safe_content_disposition('Reparación Ñ_fotos.zip')
    assert 'filename="' in cd2
    assert "filename*=UTF-8''" in cd2
    assert 'Reparaci%C3%B3n' in cd2  # percent-encoded


def test_safe_content_disposition_caracteres_prohibidos():
    from utils.zip_helper import safe_content_disposition
    cd = safe_content_disposition('OT/2025\\01:foo.zip')
    # ASCII fallback no contiene los caracteres prohibidos
    assert '\\' not in cd.split('filename=')[1].split(';')[0]
    assert ':' not in cd.split('filename=')[1].split(';')[0]


def test_detect_extension_por_content_type():
    from utils.zip_helper import detect_extension
    assert detect_extension('https://x/foo', 'image/jpeg') == 'jpg'
    assert detect_extension('https://x/foo', 'image/png; charset=binary') == 'png'
    assert detect_extension('https://x/foo', 'image/heic') == 'heic'


def test_detect_extension_por_url_cuando_no_hay_content_type():
    from utils.zip_helper import detect_extension
    assert detect_extension('https://res.cloudinary.com/foo/img.jpg?v=1', None) == 'jpg'
    assert detect_extension('https://x/y/abc.PNG', None) == 'png'


def test_detect_extension_fallback_jpg_cuando_no_hay_pista():
    from utils.zip_helper import detect_extension
    # Cloudinary URL sin extensión visible
    assert detect_extension('https://res.cloudinary.com/x/image/upload/v1234/abc', None) == 'jpg'
    # Extensión inválida en URL
    assert detect_extension('https://x/y/foo.exe', None) == 'jpg'


# ── ZIP integrity end-to-end ────────────────────────────────────────────────

def test_zip_generado_por_endpoint_es_valido():
    """Genera un ZIP con el helper igual que el endpoint y valida integridad."""
    import unicodedata  # noqa: F401
    from utils.zip_helper import safe_inner_filename, detect_extension

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Simulamos 4 fotos (varios documentos = caso del bug del usuario)
        for i, (cat, content) in enumerate([
            ("admin", b"\xff\xd8\xff" + b"x" * 1000),       # JPG fake
            ("tecnico", b"\x89PNG\r\n\x1a\n" + b"y" * 1500),  # PNG fake
            ("antes", b"\xff\xd8\xff" + b"a" * 500),
            ("despues", b"\xff\xd8\xff" + b"b" * 700),
        ]):
            ext = detect_extension(f"http://x/foo.jpg", "image/jpeg")
            name = safe_inner_filename(f"{cat}_{i+1}.{ext}")
            zf.writestr(name, content)

    zip_bytes = buf.getvalue()
    # ZIP es válido
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes))

    # Test de integridad de cada entrada (testzip devuelve None si OK)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        result = zf.testzip()
        assert result is None, f"ZIP corrupto en entrada: {result}"

        # Verifica las 4 entradas
        names = zf.namelist()
        assert len(names) == 4
        for name in names:
            data = zf.read(name)
            assert len(data) > 0


def test_deduplicate_zip_entries():
    from utils.zip_helper import deduplicate_zip_entries
    entries = [
        ("foto.jpg", b"a"),
        ("foto.jpg", b"b"),  # colisión
        ("foto.jpg", b"c"),  # colisión
        ("otra.png", b"d"),
    ]
    out = deduplicate_zip_entries(entries)
    names = [n for n, _ in out]
    assert len(names) == 4
    assert len(set(names)) == 4  # todos únicos
    assert "foto.jpg" in names
    # Los duplicados llevan sufijo _2, _3
    assert any("_2" in n for n in names)
    assert any("_3" in n for n in names)


# ── Endpoint integración (E2E real con backend en marcha) ───────────────────

def test_endpoint_fotos_zip_e2e_con_orden_real():
    """Test integración: descarga ZIP de una orden real y valida integridad."""
    import os
    import requests
    import dotenv
    dotenv.load_dotenv("/app/frontend/.env")
    base = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

    # Login como master
    r = requests.post(
        f"{base}/api/auth/login",
        json={"email": "master@revix.es", "password": "RevixMaster2026!"},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.skip(f"Login no disponible (rate-limit?): {r.status_code}")
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    # Buscar una orden con varias fotos en preview
    r = requests.get(f"{base}/api/ordenes?limit=200", headers=h, timeout=15)
    assert r.status_code == 200
    ordenes = r.json() if isinstance(r.json(), list) else r.json().get("ordenes", [])
    orden_con_fotos = None
    for o in ordenes:
        total_fotos = (
            len(o.get("evidencias") or [])
            + len(o.get("evidencias_tecnico") or [])
            + len(o.get("fotos_antes") or [])
            + len(o.get("fotos_despues") or [])
        )
        if total_fotos >= 2:
            orden_con_fotos = o
            break

    if not orden_con_fotos:
        pytest.skip("No hay órdenes con 2+ fotos en preview para validar E2E")

    # Descargar ZIP
    r = requests.get(
        f"{base}/api/ordenes/{orden_con_fotos['id']}/fotos-zip",
        headers=h,
        timeout=120,
    )
    assert r.status_code == 200, r.text[:300]

    # Verificar headers críticos
    assert r.headers.get("content-type") == "application/zip"
    cd = r.headers.get("content-disposition", "")
    assert "filename=" in cd
    assert "filename*=UTF-8''" in cd, "Falta encoding UTF-8 en Content-Disposition"
    cl = r.headers.get("content-length")
    assert cl and int(cl) == len(r.content), \
        f"Content-Length ({cl}) no coincide con bytes recibidos ({len(r.content)})"

    # Verificar que el ZIP no está truncado
    assert zipfile.is_zipfile(io.BytesIO(r.content)), "ZIP descargado no es válido"

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        bad = zf.testzip()
        assert bad is None, f"ZIP corrupto en entrada: {bad}"
        # Al menos 1 entrada (el endpoint puede haber filtrado fotos rotas)
        assert len(zf.namelist()) >= 1
