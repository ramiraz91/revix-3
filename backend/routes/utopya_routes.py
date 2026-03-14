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

async def extract_ean_sku_from_product_page(page, url: str) -> dict:
    """
    Extrae EAN y SKU de la página individual del producto en Utopya.
    Utopya muestra: "SKU\n179741\nEAN\n661-56050\nGarantía"
    """
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(2)
        
        result = await page.evaluate('''() => {
            const bodyText = document.body.innerText;
            let ean = '';
            let sku = '';
            
            // Extraer SKU: buscar "SKU" seguido de valor en siguiente línea
            const skuMatch = bodyText.match(/\\bSKU\\s*\\n([^\\n]+)/i);
            if (skuMatch && skuMatch[1]) {
                const val = skuMatch[1].trim();
                if (val && val.length >= 3 && !/^(N\\/D|N\\/A|No disponible|-)$/i.test(val)) {
                    sku = val;
                }
            }
            
            // Extraer EAN: buscar "EAN" seguido de valor en siguiente línea
            const eanMatch = bodyText.match(/\\bEAN\\s*\\n([^\\n]+)/i);
            if (eanMatch && eanMatch[1]) {
                const val = eanMatch[1].trim();
                if (val && val.length > 3 && !/^(N\\/D|N\\/A|No disponible|-)$/i.test(val)) {
                    ean = val;
                }
            }
            
            // Fallback: buscar en tabla de atributos
            if (!ean || !sku) {
                const rows = document.querySelectorAll('.additional-attributes tr, .product-info-main tr, table tr');
                for (const row of rows) {
                    const cells = row.querySelectorAll('th, td');
                    for (let i = 0; i < cells.length - 1; i++) {
                        const label = cells[i]?.textContent?.trim().toLowerCase() || '';
                        const value = cells[i + 1]?.textContent?.trim() || '';
                        if (!ean && (label === 'ean' || label.includes('ean'))) {
                            if (value.length > 3 && !/^(N\\/D|N\\/A|-)$/i.test(value)) ean = value;
                        }
                        if (!sku && (label === 'sku' || label.includes('sku'))) {
                            if (value.length >= 3 && !/^(N\\/D|N\\/A|-)$/i.test(value)) sku = value;
                        }
                    }
                }
            }
            
            return { ean: ean, sku: sku };
        }''')
        
        return result or {'ean': '', 'sku': ''}
    except Exception as e:
        logger.warning(f"Utopya: Error extrayendo EAN/SKU de {url}: {e}")
        return {'ean': '', 'sku': ''}


async def _scrape_utopya_httpx(email: str, password: str, urls_to_scrape: list) -> list:
    """Fallback: scrapear Utopya usando httpx cuando Playwright no está disponible."""
    import httpx
    from html.parser import HTMLParser
    
    all_products = []
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Login
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9',
        }
        
        # Get login page for form key
        login_page = await client.get('https://www.utopya.es/es/customer/account/login/', headers=headers)
        
        # Extract form_key
        import re as _re
        form_key_match = _re.search(r'name="form_key"\s+value="([^"]+)"', login_page.text)
        form_key = form_key_match.group(1) if form_key_match else ''
        
        # Submit login
        login_data = {
            'form_key': form_key,
            'login[username]': email,
            'login[password]': password,
            'send': '',
        }
        login_headers = {**headers, 'Content-Type': 'application/x-www-form-urlencoded'}
        await client.post('https://www.utopya.es/es/customer/account/loginPost/', data=login_data, headers=login_headers)
        
        logger.info("Utopya httpx: Login enviado")
        
        for cat_idx, cat_info in enumerate(urls_to_scrape):
            if not utopya_sync_progress["running"]:
                break
            
            utopya_sync_progress["current_category"] = cat_info["name"]
            
            try:
                page_num = 1
                while page_num <= 100:
                    url = cat_info["url"]
                    if page_num > 1:
                        url += f"?p={page_num}"
                    
                    resp = await client.get(url, headers=headers)
                    html = resp.text
                    
                    # Parse products from HTML
                    products_on_page = []
                    
                    # Find product items using regex
                    product_blocks = _re.findall(r'<li[^>]*class="[^"]*product-item[^"]*"[^>]*>(.*?)</li>', html, _re.DOTALL)
                    
                    for block in product_blocks:
                        name_match = _re.search(r'class="product-item-link"[^>]*>\s*([^<]+)', block)
                        price_match = _re.search(r'data-price-amount="([^"]+)"', block)
                        link_match = _re.search(r'<a[^>]*class="product-item-link"[^>]*href="([^"]+)"', block)
                        img_match = _re.search(r'<img[^>]*class="[^"]*product-image-photo[^"]*"[^>]*src="([^"]+)"', block)
                        
                        name = name_match.group(1).strip() if name_match else ''
                        price = float(price_match.group(1)) if price_match else 0
                        link = link_match.group(1) if link_match else ''
                        img = img_match.group(1) if img_match else ''
                        
                        if name and len(name) > 3:
                            products_on_page.append({
                                'nombre': name,
                                'precio': price,
                                'ean': '',
                                'imagen': img,
                                'url': link,
                                'marca': cat_info['marca'],
                                'categoria_utopya': cat_info['name']
                            })
                    
                    if not products_on_page:
                        break
                    
                    all_products.extend(products_on_page)
                    utopya_sync_progress["total"] = len(all_products)
                    logger.info(f"Utopya httpx: {cat_info['name']} p{page_num}: {len(products_on_page)} productos ({len(all_products)} total)")
                    
                    # Check if there's a next page
                    if 'class="action  next"' not in html and 'class="action next"' not in html:
                        break
                    
                    page_num += 1
                    await asyncio.sleep(1)
                
                utopya_sync_progress["categories_done"] = cat_idx + 1
                
            except Exception as e:
                logger.error(f"Utopya httpx: Error en {cat_info['name']}: {e}")
                utopya_sync_progress["errors"] += 1
        
        # Extract EAN/SKU from individual product pages
        utopya_sync_progress["status"] = "extracting_details"
        for idx, product in enumerate(all_products):
            if not utopya_sync_progress["running"]:
                break
            product_url = product.get("url", "")
            if product_url:
                try:
                    resp = await client.get(product_url, headers=headers)
                    html = resp.text
                    
                    # Extract SKU
                    sku_match = _re.search(r'SKU\s*</[^>]+>\s*<[^>]+>\s*([^<]+)', html)
                    if not sku_match:
                        sku_match = _re.search(r'>\s*SKU\s*<[^>]*>\s*<[^>]*>\s*([^<]+)', html)
                    if sku_match:
                        product["sku_utopya"] = sku_match.group(1).strip()
                    
                    # Extract EAN
                    ean_match = _re.search(r'EAN\s*</[^>]+>\s*<[^>]+>\s*([^<]+)', html)
                    if not ean_match:
                        ean_match = _re.search(r'>\s*EAN\s*<[^>]*>\s*<[^>]*>\s*([^<]+)', html)
                    if ean_match:
                        ean_val = ean_match.group(1).strip()
                        if ean_val and len(ean_val) > 3 and ean_val not in ['N/D', 'N/A', '-']:
                            product["ean"] = ean_val
                    
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
            
            if (idx + 1) % 10 == 0:
                utopya_sync_progress["processed"] = idx + 1
                logger.info(f"Utopya httpx: Detalles {idx + 1}/{len(all_products)}")
    
    return all_products




async def scrape_utopya_products(email: str, password: str, selected_categories: List[str], margen: float = 25.0):
    """Scraper principal de Utopya. Usa Playwright si disponible, httpx como fallback."""
    global utopya_sync_progress
    
    utopya_sync_progress = {
        "running": True, "total": 0, "processed": 0, "imported": 0, "updated": 0,
        "errors": 0, "current_category": "", "status": "starting",
        "last_error": None, "categories_done": 0, "categories_total": 0
    }
    
    try:
        # Construir lista de URLs
        urls_to_scrape = []
        for cat_id in selected_categories:
            parts = cat_id.split(".")
            if len(parts) == 2:
                marca, subcat = parts
                if marca in UTOPYA_CATEGORIES and subcat in UTOPYA_CATEGORIES[marca]["subcategories"]:
                    info = UTOPYA_CATEGORIES[marca]["subcategories"][subcat]
                    urls_to_scrape.append({"url": info["url"], "name": info["name"], "marca": marca})
        
        if not urls_to_scrape:
            utopya_sync_progress.update({"status": "error", "last_error": "No hay categorías válidas seleccionadas", "running": False})
            return
        
        utopya_sync_progress["categories_total"] = len(urls_to_scrape)
        
        # === FASE 1: Scraping (Playwright o httpx) ===
        all_products = await _scrape_phase(email, password, urls_to_scrape)
        
        # === FASE 2: Deduplicar ===
        utopya_sync_progress["status"] = "processing"
        seen = set()
        unique_products = []
        for p in all_products:
            key = p.get("nombre", "")
            if key and key not in seen:
                seen.add(key)
                unique_products.append(p)
        
        utopya_sync_progress["total"] = len(unique_products)
        utopya_sync_progress["processed"] = 0
        logger.info(f"Utopya: {len(unique_products)} productos únicos de {len(all_products)} totales")
        
        # === FASE 3: Importar a inventario ===
        utopya_sync_progress["status"] = "importing"
        
        for idx, product in enumerate(unique_products):
            if not utopya_sync_progress["running"]:
                break
            try:
                utopya_sync_progress["processed"] = idx + 1
                if not product.get("nombre"):
                    continue
                
                ean = product.get("ean", "").strip()
                sku_utopya = product.get("sku_utopya", "").strip()
                
                if sku_utopya:
                    sku = f"UTO-{sku_utopya}"
                elif ean and len(ean) >= 5 and ean not in ['N/D', 'N/A', '-', 'No disponible']:
                    sku = ean.replace('-', '').replace(' ', '').upper()
                else:
                    sku = f"UTO-{hashlib.md5(product['nombre'].encode()).hexdigest()[:8].upper()}"
                
                precio_compra = product.get("precio", 0)
                precio_venta = round(precio_compra * (1 + margen / 100), 2)
                categoria = product.get("categoria_utopya", "Utopya")
                marca = product.get("marca", "").capitalize() if product.get("marca") else None
                
                repuesto_data = {
                    "nombre": product["nombre"], "categoria": categoria, "categoria_utopya": categoria,
                    "marca": marca, "sku_proveedor": sku_utopya or sku, "sku_utopya": sku_utopya or None,
                    "ean": ean if ean else None, "codigo_barras": ean if ean else sku,
                    "proveedor": "Utopya", "proveedor_id": "utopya",
                    "precio_compra": precio_compra, "precio_venta": precio_venta,
                    "imagen_url": product.get("imagen"), "url_proveedor": product.get("url"),
                    "ultima_sync": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                search_conditions = [
                    {"nombre": product["nombre"], "proveedor": "Utopya"},
                    {"sku_proveedor": sku, "proveedor": "Utopya"}
                ]
                if ean:
                    search_conditions.append({"ean": ean, "proveedor": "Utopya"})
                
                existing = await db.repuestos.find_one({"$or": search_conditions})
                if existing:
                    await db.repuestos.update_one({"_id": existing["_id"]}, {"$set": repuesto_data})
                    utopya_sync_progress["updated"] += 1
                else:
                    repuesto_data.update({"id": str(uuid.uuid4()), "sku": sku, "stock": 0, "stock_minimo": 0, "created_at": datetime.now(timezone.utc).isoformat()})
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


async def _scrape_phase(email: str, password: str, urls_to_scrape: list) -> list:
    """Fase de scraping: intenta Playwright, fallback a httpx."""
    try:
        from playwright.async_api import async_playwright
        try:
            from playwright_stealth import Stealth
            use_stealth = True
        except ImportError:
            use_stealth = False
            logger.warning("Utopya: playwright_stealth no disponible, usando Playwright básico")
        return await _scrape_with_playwright(email, password, urls_to_scrape, use_stealth)
    except ImportError:
        logger.warning("Utopya: Playwright no disponible, usando httpx")
    except Exception as e:
        logger.warning(f"Utopya: Playwright falló ({e}), usando httpx")
    return await _scrape_utopya_httpx(email, password, urls_to_scrape)


async def _scrape_with_playwright(email: str, password: str, urls_to_scrape: list, use_stealth: bool) -> list:
    """Scraping con Playwright."""
    global utopya_sync_progress
    from playwright.async_api import async_playwright
    
    all_products = []
    
    async with async_playwright() as p:
        if use_stealth:
            from playwright_stealth import Stealth
            Stealth().hook_playwright_context(p)
        
        utopya_sync_progress["status"] = "launching_browser"
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Login
        utopya_sync_progress["status"] = "logging_in"
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
        
        utopya_sync_progress["status"] = "scraping"
        
        _js_extract = '''() => {
            const items = [];
            document.querySelectorAll('.product-item, .item.product').forEach(el => {
                try {
                    const n = el.querySelector('.product-item-link, .product-name')?.textContent?.trim();
                    const p = el.querySelector('.price, [data-price-amount]');
                    let pt = p?.getAttribute('data-price-amount') || p?.textContent || '0';
                    pt = pt.replace(/[^\\d.,]/g, '').replace(',', '.');
                    if (n && n.length > 3) items.push({
                        nombre: n, precio: parseFloat(pt) || 0, ean: '',
                        imagen: el.querySelector('img.product-image-photo')?.src || '',
                        url: el.querySelector('a.product-item-link, a.product-name')?.href || ''
                    });
                } catch(e) {}
            });
            return items;
        }'''
        
        for cat_idx, cat_info in enumerate(urls_to_scrape):
            if not utopya_sync_progress["running"]:
                break
            utopya_sync_progress["current_category"] = cat_info["name"]
            try:
                await page.goto(cat_info["url"], timeout=60000)
                await asyncio.sleep(5)
                
                page_products = await page.evaluate(_js_extract)
                for prod in page_products:
                    prod["marca"] = cat_info["marca"]
                    prod["categoria_utopya"] = cat_info["name"]
                all_products.extend(page_products)
                utopya_sync_progress["total"] = len(all_products)
                
                # Pagination
                page_num = 1
                while page_num < 100 and utopya_sync_progress["running"]:
                    next_btn = page.locator('a.action.next, .pages-item-next a, a[title="Siguiente"]')
                    try:
                        if await next_btn.count() > 0 and await next_btn.first.is_visible():
                            await next_btn.first.click()
                            await asyncio.sleep(3)
                            page_num += 1
                            more = await page.evaluate(_js_extract)
                            for prod in more:
                                prod["marca"] = cat_info["marca"]
                                prod["categoria_utopya"] = cat_info["name"]
                            all_products.extend(more)
                            utopya_sync_progress["total"] = len(all_products)
                        else:
                            break
                    except Exception:
                        break
                
                utopya_sync_progress["categories_done"] = cat_idx + 1
            except Exception as e:
                logger.error(f"Utopya: Error en {cat_info['name']}: {e}")
                utopya_sync_progress["errors"] += 1
        
        # Extract EAN/SKU from product detail pages
        utopya_sync_progress["status"] = "extracting_details"
        detail_page = await context.new_page()
        for idx, product in enumerate(all_products):
            if not utopya_sync_progress["running"]:
                break
            if product.get("url"):
                try:
                    details = await extract_ean_sku_from_product_page(detail_page, product["url"])
                    if details.get("ean"):
                        product["ean"] = details["ean"]
                    if details.get("sku"):
                        product["sku_utopya"] = details["sku"]
                except Exception:
                    pass
            if (idx + 1) % 10 == 0:
                utopya_sync_progress["processed"] = idx + 1
        await detail_page.close()
        await browser.close()
    
    return all_products

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
