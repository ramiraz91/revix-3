"""
Utopya.es Scraper Integration
Scraping del catálogo de Utopya.es para sincronización de productos.
Usa Playwright con Stealth para bypasear Cloudflare.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import asyncio
import uuid
import re
import os
import hashlib

# Configurar path de browsers de Playwright
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'

from config import db, logger
from auth import require_auth, require_master

router = APIRouter(prefix="/utopya", tags=["Utopya"])

# ==================== CATEGORÍAS DISPONIBLES ====================

UTOPYA_CATEGORIES = {
    "apple": {
        "name": "Apple",
        "subcategories": {
            "iphone": {"name": "iPhone", "url": "https://www.utopya.es/apple/iphone.html"},
            "ipad": {"name": "iPad", "url": "https://www.utopya.es/apple/ipad.html"},
            "ipad-pro": {"name": "iPad Pro", "url": "https://www.utopya.es/apple/ipad-pro.html"},
            "ipad-air": {"name": "iPad Air", "url": "https://www.utopya.es/apple/ipad-air.html"},
            "ipad-mini": {"name": "iPad mini", "url": "https://www.utopya.es/apple/ipad-mini.html"},
            "apple-watch": {"name": "Apple Watch", "url": "https://www.utopya.es/apple/apple-watch.html"},
            "macbook": {"name": "MacBook", "url": "https://www.utopya.es/apple/macbook.html"},
            "airpods": {"name": "AirPods", "url": "https://www.utopya.es/apple/airpods.html"},
        }
    },
    "samsung": {
        "name": "Samsung",
        "subcategories": {
            "galaxy-a": {"name": "Galaxy A", "url": "https://www.utopya.es/samsung/galaxy-a.html"},
            "galaxy-s": {"name": "Galaxy S", "url": "https://www.utopya.es/samsung/galaxy-s.html"},
            "galaxy-m": {"name": "Galaxy M", "url": "https://www.utopya.es/samsung/galaxy-m.html"},
            "galaxy-j": {"name": "Galaxy J", "url": "https://www.utopya.es/samsung/galaxy-j.html"},
            "galaxy-tab": {"name": "Galaxy Tab", "url": "https://www.utopya.es/samsung/galaxy-tab.html"},
            "galaxy-xcover": {"name": "Galaxy XCover", "url": "https://www.utopya.es/samsung/galaxy-xcover.html"},
            "galaxy-z": {"name": "Galaxy Z (Fold/Flip)", "url": "https://www.utopya.es/samsung/galaxy-z.html"},
            "galaxy-note": {"name": "Galaxy Note", "url": "https://www.utopya.es/samsung/galaxy-note.html"},
            "galaxy-watch": {"name": "Galaxy Watch", "url": "https://www.utopya.es/samsung/galaxy-watch.html"},
        }
    },
    "xiaomi": {
        "name": "Xiaomi",
        "subcategories": {
            "xiaomi-serie": {"name": "Xiaomi Serie", "url": "https://www.utopya.es/xiaomi/xiaomi-serie.html"},
            "redmi": {"name": "Redmi", "url": "https://www.utopya.es/xiaomi/redmi.html"},
            "redmi-note": {"name": "Redmi Note", "url": "https://www.utopya.es/xiaomi/redmi-note.html"},
            "poco": {"name": "POCO", "url": "https://www.utopya.es/xiaomi/poco.html"},
        }
    },
    "huawei": {
        "name": "Huawei",
        "subcategories": {
            "huawei-p": {"name": "Huawei P", "url": "https://www.utopya.es/huawei/huawei-p.html"},
            "huawei-mate": {"name": "Huawei Mate", "url": "https://www.utopya.es/huawei/huawei-mate.html"},
            "honor": {"name": "Honor", "url": "https://www.utopya.es/huawei/honor.html"},
        }
    },
    "honor": {
        "name": "Honor",
        "subcategories": {
            "honor": {"name": "Honor", "url": "https://www.utopya.es/honor.html"},
        }
    },
    "motorola": {
        "name": "Motorola",
        "subcategories": {
            "motorola": {"name": "Motorola", "url": "https://www.utopya.es/motorola.html"},
        }
    },
    "oppo": {
        "name": "OPPO",
        "subcategories": {
            "oppo": {"name": "OPPO", "url": "https://www.utopya.es/oppo.html"},
        }
    },
    "oneplus": {
        "name": "OnePlus",
        "subcategories": {
            "oneplus": {"name": "OnePlus", "url": "https://www.utopya.es/oneplus.html"},
        }
    },
    "realme": {
        "name": "Realme",
        "subcategories": {
            "realme": {"name": "Realme", "url": "https://www.utopya.es/realme.html"},
        }
    },
    "google": {
        "name": "Google",
        "subcategories": {
            "pixel": {"name": "Google Pixel", "url": "https://www.utopya.es/google.html"},
        }
    },
    "otros": {
        "name": "Otros",
        "subcategories": {
            "lg": {"name": "LG", "url": "https://www.utopya.es/lg.html"},
            "sony": {"name": "Sony", "url": "https://www.utopya.es/sony.html"},
            "nokia": {"name": "Nokia", "url": "https://www.utopya.es/nokia.html"},
            "asus": {"name": "Asus", "url": "https://www.utopya.es/asus.html"},
            "tcl": {"name": "TCL", "url": "https://www.utopya.es/tcl.html"},
            "zte": {"name": "ZTE", "url": "https://www.utopya.es/zte.html"},
            "vivo": {"name": "Vivo", "url": "https://www.utopya.es/vivo.html"},
            "nothing": {"name": "Nothing", "url": "https://www.utopya.es/nothing.html"},
        }
    },
    "accesorios": {
        "name": "Accesorios",
        "subcategories": {
            "accesorios": {"name": "Accesorios", "url": "https://www.utopya.es/accesorios.html"},
            "proteccion": {"name": "Protección", "url": "https://www.utopya.es/proteccion.html"},
        }
    },
    "herramientas": {
        "name": "Herramientas",
        "subcategories": {
            "herramientas": {"name": "Herramientas", "url": "https://www.utopya.es/herramientas.html"},
            "informatica": {"name": "Informática", "url": "https://www.utopya.es/informatica.html"},
        }
    }
}

# ==================== PROGRESS TRACKING ====================

utopya_sync_progress = {
    "running": False,
    "total": 0,
    "processed": 0,
    "imported": 0,
    "updated": 0,
    "errors": 0,
    "current_category": "",
    "status": "idle",
    "last_error": None,
    "categories_done": 0,
    "categories_total": 0
}

# ==================== HELPER FUNCTIONS ====================

async def get_utopya_config():
    """Obtener configuración de Utopya"""
    config = await db.configuracion.find_one({"tipo": "utopya"}, {"_id": 0})
    return config or {}

async def save_utopya_config(config: dict):
    """Guardar configuración de Utopya"""
    config["tipo"] = "utopya"
    await db.configuracion.update_one(
        {"tipo": "utopya"},
        {"$set": config},
        upsert=True
    )

# ==================== SCRAPER ====================

async def extract_ean_from_product_page(page, url: str) -> str:
    """
    Extrae el EAN/Referencia de la página individual del producto.
    Utopya muestra el EAN en la tabla de especificaciones del producto.
    El formato puede ser numérico (EAN-13) o alfanumérico con guiones (ref. fabricante).
    """
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        
        ean = await page.evaluate('''() => {
            // Método 1: Buscar específicamente la fila "EAN" en el texto de la página
            // Utopya muestra: "SKU\\n179741\\nEAN\\n661-56050\\nGarantía"
            const bodyText = document.body.innerText;
            
            // Buscar patrón: EAN seguido de un valor en la siguiente línea
            const eanLineMatch = bodyText.match(/\\bEAN\\s*\\n([^\\n]+)/i);
            if (eanLineMatch && eanLineMatch[1]) {
                const eanValue = eanLineMatch[1].trim();
                // Aceptar valores alfanuméricos con guiones (ej: 661-56050)
                if (eanValue && eanValue.length > 3 && !/^(N\\/D|N\\/A|No disponible|-)$/i.test(eanValue)) {
                    return eanValue;
                }
            }
            
            // Método 2: Buscar en tabla de atributos
            const rows = document.querySelectorAll('.additional-attributes tr, .product-info-main tr, table tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('th, td');
                for (let i = 0; i < cells.length - 1; i++) {
                    const label = cells[i]?.textContent?.trim().toLowerCase() || '';
                    if (label === 'ean' || label.includes('ean')) {
                        const value = cells[i + 1]?.textContent?.trim();
                        if (value && value.length > 3 && !/^(N\\/D|N\\/A|No disponible|-)$/i.test(value)) {
                            return value;
                        }
                    }
                }
            }
            
            // Método 3: Buscar EAN numérico estándar (13 dígitos)
            const eanNumMatch = bodyText.match(/\\bEAN[:\\s]+([\\d]{13})\\b/i);
            if (eanNumMatch) {
                return eanNumMatch[1];
            }
            
            // Método 4: Buscar en data attributes
            const productEl = document.querySelector('[data-ean], [data-gtin]');
            if (productEl) {
                const ean = productEl.getAttribute('data-ean') || productEl.getAttribute('data-gtin');
                if (ean && ean.length > 3) {
                    return ean;
                }
            }
            
            return '';
        }''')
        
        return ean or ''
    except Exception as e:
        logger.warning(f"Utopya: Error extrayendo EAN de {url}: {e}")
        return ''

async def scrape_utopya_products(email: str, password: str, selected_categories: List[str], margen: float = 25.0):
    """
    Scraper principal de Utopya usando Playwright con Stealth.
    Solo descarga las categorías seleccionadas por el usuario.
    """
    global utopya_sync_progress
    
    utopya_sync_progress = {
        "running": True,
        "total": 0,
        "processed": 0,
        "imported": 0,
        "updated": 0,
        "errors": 0,
        "current_category": "",
        "status": "starting",
        "last_error": None,
        "categories_done": 0,
        "categories_total": 0
    }
    
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        
        stealth = Stealth()
        
        # Construir lista de URLs a scrapear desde las categorías seleccionadas
        urls_to_scrape = []
        for cat_id in selected_categories:
            parts = cat_id.split(".")
            if len(parts) == 2:
                marca, subcat = parts
                if marca in UTOPYA_CATEGORIES and subcat in UTOPYA_CATEGORIES[marca]["subcategories"]:
                    url = UTOPYA_CATEGORIES[marca]["subcategories"][subcat]["url"]
                    name = UTOPYA_CATEGORIES[marca]["subcategories"][subcat]["name"]
                    urls_to_scrape.append({"url": url, "name": name, "marca": marca})
        
        if not urls_to_scrape:
            utopya_sync_progress["status"] = "error"
            utopya_sync_progress["last_error"] = "No hay categorías válidas seleccionadas"
            utopya_sync_progress["running"] = False
            return
        
        utopya_sync_progress["categories_total"] = len(urls_to_scrape)
        logger.info(f"Utopya: {len(urls_to_scrape)} categorías a scrapear")
        
        async with async_playwright() as p:
            stealth.hook_playwright_context(p)
            
            utopya_sync_progress["status"] = "launching_browser"
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # Login
            utopya_sync_progress["status"] = "logging_in"
            logger.info("Utopya: Realizando login...")
            
            await page.goto('https://www.utopya.es/es/customer/account/login/', timeout=60000)
            await asyncio.sleep(8)
            
            try:
                await page.fill('#email', email)
                await page.fill('#pass', password)
                await page.click('#send2')
                await asyncio.sleep(5)
                logger.info("Utopya: Login completado")
            except Exception as e:
                logger.error(f"Utopya: Error en login: {e}")
            
            all_products = []
            
            # Scrapear cada categoría seleccionada
            utopya_sync_progress["status"] = "scraping"
            
            for cat_idx, cat_info in enumerate(urls_to_scrape):
                if not utopya_sync_progress["running"]:
                    break
                    
                try:
                    utopya_sync_progress["current_category"] = cat_info["name"]
                    utopya_sync_progress["categories_done"] = cat_idx
                    logger.info(f"Utopya: Scrapeando {cat_info['name']} ({cat_idx+1}/{len(urls_to_scrape)})...")
                    
                    await page.goto(cat_info["url"], timeout=60000)
                    await asyncio.sleep(3)
                    
                    # Extraer productos de la página de listado
                    # Utopya muestra el EAN en el listado, lo usamos como SKU
                    page_products = await page.evaluate('''() => {
                        const items = [];
                        document.querySelectorAll('.product-item, .item.product').forEach(el => {
                            try {
                                const nameEl = el.querySelector('.product-item-link, .product-name');
                                const priceEl = el.querySelector('.price, [data-price-amount]');
                                const imgEl = el.querySelector('img.product-image-photo');
                                const linkEl = el.querySelector('a.product-item-link, a.product-name');
                                
                                const name = nameEl?.textContent?.trim();
                                let priceText = priceEl?.getAttribute('data-price-amount') || priceEl?.textContent || '0';
                                priceText = priceText.replace(/[^\\d.,]/g, '').replace(',', '.');
                                const price = parseFloat(priceText) || 0;
                                const productUrl = linkEl?.href || '';
                                
                                // Buscar EAN en diferentes lugares
                                let ean = '';
                                // Buscar en data attributes
                                const eanEl = el.querySelector('[data-ean], [data-gtin], .ean-value, .product-ean');
                                if (eanEl) {
                                    ean = eanEl.getAttribute('data-ean') || eanEl.getAttribute('data-gtin') || eanEl.textContent?.trim() || '';
                                }
                                // Buscar en SKU que a veces contiene el EAN
                                if (!ean) {
                                    const skuEl = el.querySelector('.sku .value, .product-sku');
                                    const skuText = skuEl?.textContent?.trim() || '';
                                    // Si el SKU parece un EAN (13 dígitos), usarlo
                                    if (/^\\d{13}$/.test(skuText)) {
                                        ean = skuText;
                                    }
                                }
                                
                                if (name && name.length > 3) {
                                    items.push({
                                        nombre: name,
                                        precio: price,
                                        ean: ean,
                                        imagen: imgEl?.src || '',
                                        url: productUrl
                                    });
                                }
                            } catch(e) {}
                        });
                        return items;
                    }''')
                    
                    for prod in page_products:
                        prod["marca"] = cat_info["marca"]
                        prod["categoria_utopya"] = cat_info["name"]
                    
                    all_products.extend(page_products)
                    utopya_sync_progress["total"] = len(all_products)
                    logger.info(f"Utopya: {len(page_products)} productos en {cat_info['name']} (página 1)")
                    
                    # Buscar paginación y obtener más páginas
                    page_num = 1
                    max_pages = 100  # Aumentar límite de páginas
                    while page_num < max_pages and utopya_sync_progress["running"]:
                        # Buscar botón de siguiente página
                        next_btn = page.locator('a.action.next, .pages-item-next a, a[title="Siguiente"]')
                        
                        has_next = False
                        try:
                            if await next_btn.count() > 0:
                                first_btn = next_btn.first
                                if await first_btn.is_visible():
                                    has_next = True
                        except Exception:
                            has_next = False
                        
                        if not has_next:
                            break
                        
                        try:
                            await next_btn.first.click()
                            await asyncio.sleep(3)
                            page_num += 1
                            
                            more_products = await page.evaluate('''() => {
                                const items = [];
                                document.querySelectorAll('.product-item, .item.product').forEach(el => {
                                    const nameEl = el.querySelector('.product-item-link, .product-name');
                                    const priceEl = el.querySelector('.price, [data-price-amount]');
                                    const imgEl = el.querySelector('img.product-image-photo');
                                    const linkEl = el.querySelector('a.product-item-link, a.product-name');
                                    
                                    const name = nameEl?.textContent?.trim();
                                    let priceText = priceEl?.getAttribute('data-price-amount') || priceEl?.textContent || '0';
                                    priceText = priceText.replace(/[^\\d.,]/g, '').replace(',', '.');
                                    const productUrl = linkEl?.href || '';
                                    
                                    // Buscar EAN
                                    let ean = '';
                                    const eanEl = el.querySelector('[data-ean], [data-gtin], .ean-value, .product-ean');
                                    if (eanEl) {
                                        ean = eanEl.getAttribute('data-ean') || eanEl.getAttribute('data-gtin') || eanEl.textContent?.trim() || '';
                                    }
                                    if (!ean) {
                                        const skuEl = el.querySelector('.sku .value, .product-sku');
                                        const skuText = skuEl?.textContent?.trim() || '';
                                        if (/^\\d{13}$/.test(skuText)) {
                                            ean = skuText;
                                        }
                                    }
                                    
                                    if (name && name.length > 3) {
                                        items.push({
                                            nombre: name,
                                            precio: parseFloat(priceText) || 0,
                                            ean: ean,
                                            imagen: imgEl?.src || '',
                                            url: productUrl
                                        });
                                    }
                                });
                                return items;
                            }''')
                            
                            for prod in more_products:
                                prod["marca"] = cat_info["marca"]
                                prod["categoria_utopya"] = cat_info["name"]
                            
                            all_products.extend(more_products)
                            utopya_sync_progress["total"] = len(all_products)
                            logger.info(f"Utopya: Página {page_num} de {cat_info['name']}: {len(more_products)} productos ({len(all_products)} total)")
                        except Exception as e:
                            logger.warning(f"Utopya: Error en paginación página {page_num}: {e}")
                            break
                    
                    utopya_sync_progress["categories_done"] = cat_idx + 1
                    
                except Exception as e:
                    logger.error(f"Utopya: Error en {cat_info['name']}: {e}")
                    utopya_sync_progress["errors"] += 1
                    continue
            
            await browser.close()
            
            # Procesar e importar productos
            utopya_sync_progress["status"] = "processing"
            logger.info(f"Utopya: Procesando {len(all_products)} productos...")
            
            # Eliminar duplicados
            seen = set()
            unique_products = []
            for p in all_products:
                key = p.get("nombre", "")
                if key and key not in seen:
                    seen.add(key)
                    unique_products.append(p)
            
            utopya_sync_progress["total"] = len(unique_products)
            logger.info(f"Utopya: {len(unique_products)} productos únicos")
            
            for idx, product in enumerate(unique_products):
                if not utopya_sync_progress["running"]:
                    break
                    
                try:
                    utopya_sync_progress["processed"] = idx + 1
                    
                    if not product.get("nombre"):
                        continue
                    
                    # Usar EAN como SKU si está disponible, sino generar hash del nombre
                    ean = product.get("ean", "").strip()
                    # Aceptar EAN numérico o alfanumérico (con guiones, como 661-56050)
                    if ean and len(ean) >= 5 and ean not in ['N/D', 'N/A', '-', 'No disponible']:
                        sku = ean.replace('-', '').replace(' ', '').upper()  # Normalizar para SKU
                    else:
                        # Fallback: generar SKU basado en hash del nombre
                        nombre_hash = hashlib.md5(product["nombre"].encode()).hexdigest()[:8].upper()
                        sku = f"UTO-{nombre_hash}"
                    
                    precio_compra = product.get("precio", 0)
                    precio_venta = round(precio_compra * (1 + margen / 100), 2)
                    
                    categoria = product.get("categoria_utopya", "Utopya")
                    marca = product.get("marca", "").capitalize() if product.get("marca") else None
                    
                    repuesto_data = {
                        "nombre": product["nombre"],
                        "categoria": categoria,
                        "categoria_utopya": categoria,
                        "marca": marca,
                        "sku_proveedor": sku,
                        "ean": ean if ean else None,  # Guardar EAN original
                        "codigo_barras": ean if ean else sku,  # Código de barras = EAN
                        "proveedor": "Utopya",
                        "proveedor_id": "utopya",
                        "precio_compra": precio_compra,
                        "precio_venta": precio_venta,
                        "imagen_url": product.get("imagen"),
                        "url_proveedor": product.get("url"),
                        "ultima_sync": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Buscar por EAN, nombre o SKU (para actualizaciones)
                    search_conditions = [
                        {"nombre": product["nombre"], "proveedor": "Utopya"},
                        {"sku_proveedor": sku, "proveedor": "Utopya"}
                    ]
                    if ean:
                        search_conditions.append({"ean": ean, "proveedor": "Utopya"})
                    
                    existing = await db.repuestos.find_one({
                        "$or": search_conditions
                    })
                    
                    if existing:
                        await db.repuestos.update_one(
                            {"_id": existing["_id"]},
                            {"$set": repuesto_data}
                        )
                        utopya_sync_progress["updated"] += 1
                    else:
                        repuesto_data["id"] = str(uuid.uuid4())
                        repuesto_data["sku"] = sku
                        # codigo_barras ya está en repuesto_data con el EAN
                        repuesto_data["stock"] = 0
                        repuesto_data["stock_minimo"] = 0
                        repuesto_data["created_at"] = datetime.now(timezone.utc).isoformat()
                        
                        await db.repuestos.insert_one(repuesto_data)
                        utopya_sync_progress["imported"] += 1
                    
                except Exception:
                    utopya_sync_progress["errors"] += 1
            
            config = await get_utopya_config()
            config["last_sync"] = datetime.now(timezone.utc).isoformat()
            config["last_sync_count"] = utopya_sync_progress["imported"] + utopya_sync_progress["updated"]
            await save_utopya_config(config)
            
            utopya_sync_progress["status"] = "completed"
            logger.info(f"Utopya sync completed: {utopya_sync_progress['imported']} imported, {utopya_sync_progress['updated']} updated")
            
    except Exception as e:
        utopya_sync_progress["status"] = "error"
        utopya_sync_progress["last_error"] = str(e)
        logger.error(f"Utopya sync error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        utopya_sync_progress["running"] = False

# ==================== ROUTES ====================

@router.get("/categories")
async def get_available_categories(user: dict = Depends(require_auth)):
    """Obtener categorías disponibles de Utopya"""
    return UTOPYA_CATEGORIES

@router.get("/config")
async def get_config(user: dict = Depends(require_auth)):
    """Obtener configuración de Utopya"""
    config = await get_utopya_config()
    if config.get("password"):
        config["password"] = "********"
    return config

@router.post("/config")
async def save_config(request: dict, user: dict = Depends(require_master)):
    """Guardar configuración de Utopya"""
    config = request.copy()
    config["tipo"] = "utopya"
    
    if config.get("password") == "********":
        existing = await get_utopya_config()
        config["password"] = existing.get("password", "")
    
    await save_utopya_config(config)
    return {"message": "Configuración guardada"}

@router.get("/sync-catalogo/progress")
async def get_sync_progress(user: dict = Depends(require_auth)):
    """Obtener progreso de sincronización"""
    return utopya_sync_progress

@router.post("/sync-catalogo")
async def sync_catalogo(background_tasks: BackgroundTasks, user: dict = Depends(require_master)):
    """Iniciar sincronización del catálogo de Utopya con categorías seleccionadas"""
    global utopya_sync_progress
    
    if utopya_sync_progress["running"]:
        raise HTTPException(status_code=400, detail="Ya hay una sincronización en curso")
    
    config = await get_utopya_config()
    if not config.get("email") or not config.get("password"):
        raise HTTPException(status_code=400, detail="Configura email y password de Utopya primero")
    
    selected = config.get("selected_categories", [])
    if not selected:
        raise HTTPException(status_code=400, detail="Selecciona al menos una categoría para sincronizar")
    
    margenes_config = await db.configuracion.find_one({"tipo": "margenes_proveedores"}, {"_id": 0})
    margen = 25.0
    if margenes_config and margenes_config.get("proveedores", {}).get("Utopya"):
        margen = margenes_config["proveedores"]["Utopya"].get("margen", 25.0)
    
    background_tasks.add_task(scrape_utopya_products, config["email"], config["password"], selected, margen)
    
    return {"message": "Sincronización iniciada", "margen_aplicado": margen, "categorias": len(selected)}

@router.post("/sync-catalogo/stop")
async def stop_sync(user: dict = Depends(require_master)):
    """Detener sincronización"""
    global utopya_sync_progress
    utopya_sync_progress["running"] = False
    utopya_sync_progress["status"] = "stopped"
    return {"message": "Sincronización detenida"}

@router.get("/stats")
async def get_stats(user: dict = Depends(require_auth)):
    """Estadísticas de productos de Utopya"""
    count = await db.repuestos.count_documents({"proveedor": "Utopya"})
    config = await get_utopya_config()
    
    return {
        "productos_importados": count,
        "ultima_sync": config.get("last_sync"),
        "configurado": bool(config.get("email")),
        "categorias_seleccionadas": len(config.get("selected_categories", []))
    }
