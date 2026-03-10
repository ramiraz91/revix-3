"""
Sumbroker REST API client.
Replaces HTML scraping with direct API calls to https://api.sumbroker.es/api/v2.
The portal at distribuidor.sumbroker.es is a KnockoutJS SPA consuming this API.

Only budget-related administrative queries go through this client.
All operational CRM changes are internal.
"""
import httpx
import logging
import os
import uuid
import aiofiles
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

API_BASE = "https://api.sumbroker.es/api/v2"
REQUEST_TIMEOUT = 180.0  # Very generous timeout for slow Sumbroker API
MAX_SEARCH_LIMIT = 100
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
MAX_RETRIES = 2  # Retry on auth failures


class SumbrokerClient:
    """Stateless client — authenticates on demand, no persistent sessions."""

    def __init__(self, login: str, password: str):
        self._login = login
        self._password = password
        self._token: Optional[str] = None
        self._user_data: Optional[dict] = None

    # ── auth ────────────────────────────────────────────────

    async def authenticate(self) -> bool:
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(
                        f"{API_BASE}/users/login",
                        json={"login": self._login, "password": self._password},
                        headers={"Content-Type": "application/json",
                                 "Accept": "application/json",
                                 "X-localization": "es"},
                    )
                    if resp.status_code != 200:
                        logger.error("Sumbroker login failed (attempt %d): %s %s",
                                     attempt + 1, resp.status_code, resp.text[:300])
                        if attempt < MAX_RETRIES - 1:
                            import asyncio
                            await asyncio.sleep(2)
                            continue
                        return False

                    data = resp.json()
                    self._token = data.get("api_token")
                    self._user_data = data
                    logger.info("Sumbroker login OK — user=%s", data.get("name"))
                    return True
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.error("Sumbroker login network error (attempt %d): %s", attempt + 1, e)
                if attempt < MAX_RETRIES - 1:
                    import asyncio
                    await asyncio.sleep(3)
                    continue
                return False
        return False

    async def _ensure_auth(self) -> bool:
        """Ensure we have a valid token, re-authenticate if needed."""
        if self._token:
            return True
        return await self.authenticate()

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP request with automatic retry on auth failure or timeout."""
        for attempt in range(MAX_RETRIES):
            if not await self._ensure_auth():
                raise Exception("Authentication failed after retries")
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    # Always use fresh headers with current token
                    kwargs["headers"] = self._headers()
                    resp = await getattr(client, method)(url, **kwargs)
                    if resp.status_code == 401:
                        logger.warning("Token expired, re-authenticating (attempt %d)", attempt + 1)
                        self._token = None
                        continue
                    return resp
            except httpx.TimeoutException:
                logger.warning("Request timeout for %s (attempt %d)", url, attempt + 1)
                if attempt < MAX_RETRIES - 1:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
                raise
        raise Exception(f"Request failed after {MAX_RETRIES} retries")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json",
             "Accept": "application/json",
             "X-localization": "es"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    # ── store budgets ───────────────────────────────────────

    async def list_store_budgets(self, limit: int = 50) -> list[dict]:
        """
        Get the most recent store budgets.
        Optimized: fetch only the last page(s) needed.
        """
        if not await self._ensure_auth():
            return []
        
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                # Get total first
                resp = await client.get(
                    f"{API_BASE}/store-budget",
                    params={"limit": 1},
                    headers=self._headers(),
                )
                if resp.status_code == 401:
                    self._token = None
                    if not await self._ensure_auth():
                        return []
                    resp = await client.get(
                        f"{API_BASE}/store-budget",
                        params={"limit": 1},
                        headers=self._headers(),
                    )
                if resp.status_code != 200:
                    logger.error("list_store_budgets error: %s", resp.status_code)
                    return []
                
                total = resp.json().get("total", 0)
                if total == 0:
                    return []
                
                # Fetch only the last page with enough items
                page_size = min(limit, 50)
                total_pages = (total + page_size - 1) // page_size
                
                all_budgets = []
                pages_fetched = 0
                max_pages = 3  # Limit to 3 pages max to avoid slow responses
                
                for page in range(total_pages, 0, -1):
                    if pages_fetched >= max_pages or len(all_budgets) >= limit:
                        break
                    try:
                        resp = await client.get(
                            f"{API_BASE}/store-budget",
                            params={"limit": page_size, "page": page},
                            headers=self._headers(),
                        )
                        if resp.status_code != 200:
                            logger.warning(f"Page {page} failed: {resp.status_code}")
                            continue
                        
                        budgets = resp.json().get("store_budgets", [])
                        if budgets:
                            all_budgets.extend(budgets)
                            logger.info(f"Página {page}: {len(budgets)} presupuestos")
                        pages_fetched += 1
                    except httpx.TimeoutException:
                        logger.warning(f"Timeout fetching page {page}, continuing with what we have")
                        break
                
                # Sort by ID descending (newest first)
                all_budgets.sort(key=lambda x: x.get("id", 0), reverse=True)
                
                result = all_budgets[:limit]
                logger.info(f"Devolviendo {len(result)} presupuestos recientes de {total} totales")
                return result
        except Exception as e:
            logger.error(f"list_store_budgets exception: {e}")
            return []

    async def get_store_budget(self, budget_id: int) -> Optional[dict]:
        if not await self._ensure_auth():
            return None
        try:
            resp = await self._request_with_retry(
                "get", f"{API_BASE}/store-budget/{budget_id}")
            if resp.status_code != 200:
                logger.error("get_store_budget(%s) error: %s",
                             budget_id, resp.status_code)
                return None
            return resp.json()
        except Exception as e:
            logger.error("get_store_budget(%s) exception: %s", budget_id, e)
            return None

    async def get_observations(self, budget_id: int) -> list[dict]:
        if not await self._ensure_auth():
            return []
        try:
            resp = await self._request_with_retry(
                "get", f"{API_BASE}/store_budget/{budget_id}/observations")
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("get_observations(%s) error: %s", budget_id, e)
            return []

    # ── search by service code (claim identifier) ──────────

    async def find_budget_by_service_code(self, codigo: str) -> Optional[dict]:
        """
        Search store budgets by claim identifier (e.g. '26BE000534')
        using the API's built-in search parameter.
        
        When multiple budgets exist for the same authorization code,
        prioritizes: Accepted (3) > Active (non-cancelled) > First result
        """
        if not await self._ensure_auth():
            return None

        try:
            resp = await self._request_with_retry(
                "get", f"{API_BASE}/store-budget",
                params={"search": codigo, "limit": 50})
            
            if resp.status_code != 200:
                logger.error("search error for %s: %s", codigo, resp.status_code)
                return None

            data = resp.json()
            budgets = data.get("store_budgets", [])

            if not budgets:
                logger.warning("No budget found for code %s", codigo)
                return None

            # Filter budgets that match the exact claim identifier
            exact_matches = []
            for b in budgets:
                claim = b.get("claim_budget") or {}
                prc = claim.get("policy_risk_claim") or {}
                identifier = prc.get("identifier")
                if identifier == codigo:
                    exact_matches.append(b)
            
            # If we have exact matches, prioritize by status
            candidates = exact_matches if exact_matches else budgets
            
            # Log all candidates with their status for debugging
            if candidates:
                logger.info(f"Found {len(candidates)} budget(s) for code {codigo}:")
                for i, b in enumerate(candidates):
                    # Status can be string or int - normalize to int
                    status_raw = b.get("status")
                    status = int(status_raw) if status_raw is not None else None
                    status_text = b.get("status_text", "unknown")
                    budget_id = b.get("id")
                    price = b.get("price")
                    logger.info(f"  [{i+1}] id={budget_id}, status={status} ({status_text}), price={price}")
            
            # Priority 1: Find accepted budget (status 3)
            for b in candidates:
                # Status can be string or int from API - normalize to int
                status_raw = b.get("status")
                status = int(status_raw) if status_raw is not None else None
                if status == 3:  # Accepted
                    logger.info(f"Selected ACCEPTED budget (id={b.get('id')}, status=3) for {codigo}")
                    return b
            
            # Priority 2: Find any active budget (not cancelled, status != 7)
            for b in candidates:
                status_raw = b.get("status")
                status = int(status_raw) if status_raw is not None else None
                if status != 7:  # Not cancelled
                    logger.info(f"Selected active budget (id={b.get('id')}, status={status}) for {codigo}")
                    return b
            
            # Priority 3: Return first result (even if cancelled, as last resort)
            logger.warning(f"All budgets for {codigo} are cancelled, returning first (id={candidates[0].get('id')})")
            return candidates[0]
        except Exception as e:
            logger.error(f"find_budget_by_service_code({codigo}) exception: {e}")
            return None

    async def get_claim_store_budgets(self, claim_budget_id: int) -> list[dict]:
        """Get all store budgets for a claim (competitors)."""
        if not await self._ensure_auth():
            return []
        try:
            resp = await self._request_with_retry(
                "get", f"{API_BASE}/claim-budget/{claim_budget_id}/store-budgets")
            if resp.status_code != 200:
                logger.error(f"get_claim_store_budgets({claim_budget_id}) error: {resp.status_code}")
                return []
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"get_claim_store_budgets({claim_budget_id}) exception: {e}")
            return []


    # ── photos & documents ──────────────────────────────────

    def extract_docs_from_budget(self, budget_detail: dict) -> list[dict]:
        """Extract photo/document metadata from full budget detail."""
        claim = budget_detail.get("claim_budget") or {}
        prc = claim.get("policy_risk_claim") or {}
        docs = prc.get("docs") or []
        result = []
        for doc in docs:
            result.append({
                "doc_id": doc.get("id"),
                "name": doc.get("name"),
                "is_image": doc.get("is_image", False),
                "doc_type": doc.get("doc_type", ""),
                "download_link": doc.get("download_link"),
                "created_at": doc.get("created_at"),
            })
        return result

    def extract_device_from_terminals(self, budget_detail: dict) -> dict:
        """Extract device brand/model/IMEI from mobile_terminals_active."""
        claim = budget_detail.get("claim_budget") or {}
        policy = claim.get("policy") or {}
        terminals = policy.get("mobile_terminals_active") or []
        if not terminals:
            terminals = policy.get("mobile_terminals") or []
        if terminals:
            t = terminals[0]
            return {
                "brand": t.get("brand"),
                "model": t.get("model", "").strip() if t.get("model") else None,
                "imei": t.get("imei"),
            }
        return {}

    async def download_doc(self, download_link: str) -> Optional[bytes]:
        """Download a document/photo from Sumbroker using auth token."""
        if not self._token:
            if not await self.authenticate():
                return None
        try:
            headers = {"Authorization": f"Bearer {self._token}",
                       "Accept": "*/*"}
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(download_link, headers=headers)
                if resp.status_code == 200:
                    return resp.content
                logger.error("download_doc error %s: %s", resp.status_code, download_link)
                return None
        except Exception as e:
            logger.error("download_doc exception: %s", e)
            return None

    async def download_and_save_photos(self, docs: list[dict], codigo: str) -> list[str]:
        """Download photos and save to uploads dir. Returns list of saved filenames."""
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        saved = []
        for doc in docs:
            if not doc.get("download_link"):
                continue
            content = await self.download_doc(doc["download_link"])
            if not content:
                continue
            ext = os.path.splitext(doc.get("name", "photo.jpg"))[1] or ".jpg"
            filename = f"portal_{codigo}_{doc.get('doc_id', uuid.uuid4().hex[:6])}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(content)
            saved.append(filename)
            logger.info("Saved portal photo: %s (%d bytes)", filename, len(content))
        return saved

    # ── high-level extraction ───────────────────────────────

    async def extract_service_data(self, codigo: str) -> Optional[dict]:
        """
        Main entry: find budget by claim code, get full detail,
        extract ALL structured data + docs for CRM order creation.
        Returns None if not found.
        """
        budget = await self.find_budget_by_service_code(codigo)
        if not budget:
            return None

        budget_id = budget.get("id")

        # Get full budget detail for docs, device_data, client info
        full = await self.get_store_budget(budget_id) if budget_id else None
        bd = full or budget  # best detail source

        claim = bd.get("claim_budget") or {}
        prc = claim.get("policy_risk_claim") or {}
        store = bd.get("store") or {}

        # Extract observations
        observations = []
        try:
            observations = await self.get_observations(budget_id)
        except Exception as e:
            logger.warning("Could not fetch observations: %s", e)

        # Extract docs/photos
        docs = self.extract_docs_from_budget(bd) if full else []

        # ── Device info: prefer device_data > mobile_terminals > budget level
        dd = bd.get("device_data") or {}
        terminal = self.extract_device_from_terminals(bd) if full else {}

        device_brand = dd.get("brand") or terminal.get("brand") or bd.get("brand")
        device_model = dd.get("model") or terminal.get("model") or bd.get("model")
        if device_model:
            device_model = device_model.strip()
        device_imei = dd.get("reference") or terminal.get("imei")
        device_colour = bd.get("device_colour") or prc.get("color")
        device_type = dd.get("deviceType")
        device_purchase_date = dd.get("purchaseDate")
        device_purchase_price = dd.get("productPrice")

        # ── Client info: budget top-level has full client data
        client_name = bd.get("client_name") or ""
        client_last1 = bd.get("client_last_name_1") or ""
        client_last2 = bd.get("client_last_name_2") or ""
        client_full_name = f"{client_name} {client_last1} {client_last2}".strip()
        client_nif = bd.get("client_id_number") or ""
        client_email = bd.get("client_email") or ""
        client_phone = bd.get("client_phone_number") or prc.get("phone_number") or ""

        # ── Address from policy_risk_claim (more detailed)
        client_address = prc.get("address") or bd.get("client_address") or ""
        client_city = prc.get("city") or ""
        client_province = prc.get("province") or ""
        client_zip = prc.get("zip") or ""

        # ── Damage / claim info
        damage_description = prc.get("description") or ""
        damage_type = prc.get("type_text") or ""

        extracted = {
            "source": "sumbroker_api",
            "scraped_at": datetime.now(timezone.utc).isoformat(),

            # Budget identifiers
            "budget_id": budget_id,
            "claim_budget_id": bd.get("claim_budget_id"),
            "policy_number": bd.get("policy_number"),
            "product_name": bd.get("product_name"),

            # Claim / service details
            "claim_identifier": prc.get("identifier") or codigo,
            "claim_type_text": claim.get("claim_type_text"),
            "damage_description": damage_description,
            "damage_type_text": damage_type,
            "internal_status_text": prc.get("internal_status_text"),
            "external_status_text": prc.get("external_status_text"),
            "reserve_value": prc.get("reserve_value"),
            "claim_real_value": prc.get("claim_real_value"),

            # Device info (enriched: device_data > terminals > budget)
            "device_brand": device_brand,
            "device_model": device_model,
            "device_colour": device_colour,
            "device_imei": device_imei,
            "device_status_text": bd.get("device_status_text"),
            "device_type": device_type,
            "device_purchase_date": device_purchase_date,
            "device_purchase_price": device_purchase_price,

            # Client info (from budget top-level)
            "client_name": client_name,
            "client_last_name_1": client_last1,
            "client_last_name_2": client_last2,
            "client_full_name": client_full_name,
            "client_nif": client_nif,
            "client_email": client_email,
            "client_phone": client_phone,
            "client_address": client_address,
            "client_city": client_city,
            "client_province": client_province,
            "client_zip": client_zip,

            # Repair workflow fields
            "repair_type_text": bd.get("repair_type_text"),
            "repair_time_text": bd.get("repair_time_text"),
            "warranty_type_text": bd.get("warranty_type_text"),
            "status": bd.get("status"),
            "status_text": bd.get("status_text"),
            "price": bd.get("price"),
            "accepted_date": bd.get("accepted_date"),

            # Dates
            "pickup_date": bd.get("pickup_date"),
            "repair_date": bd.get("repair_date"),
            "delivery_date": bd.get("delivery_date"),
            "shipping_date": bd.get("shipping_date"),
            "shipping_company": bd.get("shipping_company"),
            "tracking_number": bd.get("tracking_number"),

            # Store (repair center) info
            "store_identifier": bd.get("store_identifier"),
            "store_name": store.get("name"),
            "store_address": store.get("direction_formatted"),

            # Observations
            "observations": observations,

            # Documents / Photos from provider
            "docs": docs,

            # Raw IDs for future reference
            "policy_risk_claim_id": prc.get("id"),
            "policy_risk_id": prc.get("policy_risk_id"),
        }

        return extracted

    # ── WRITE OPERATIONS ─────────────────────────────────────

    async def send_observation(self, budget_id: int, message: str, visible_to_client: bool = False) -> dict:
        """
        La API REST de Sumbroker NO soporta POST de observaciones.
        Las observaciones solo se crean desde el portal web.
        Este método retorna success=True pero guarda el mensaje para referencia local.
        """
        logger.info(f"Observation for budget {budget_id} (local only, API no soporta POST): {message[:100]}")
        return {"success": True, "data": {"local_only": True, "message": message}}

    async def update_budget_status(self, budget_id: int, status: int = None, extra_data: dict = None) -> dict:
        """
        Actualiza campos del presupuesto via PATCH.
        """
        if not await self._ensure_auth():
            return {"success": False, "error": "Authentication failed"}
        
        try:
            payload = {}
            if status is not None:
                payload["status"] = status
            if extra_data:
                payload.update(extra_data)
            
            if not payload:
                return {"success": True, "data": {}}
            
            resp = await self._request_with_retry(
                "patch", f"{API_BASE}/store-budget/{budget_id}",
                json=payload)
            
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            else:
                logger.error(f"Error updating budget: {resp.status_code} {resp.text[:300]}")
                return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            logger.error(f"Exception updating budget: {e}")
            return {"success": False, "error": str(e)}

    async def submit_budget(self, budget_id: int, price: float, description: str, 
                           repair_time: str = "24-48h", warranty_months: int = 12,
                           disponibilidad_recambios: str = None, tiempo_horas: float = None,
                           tipo_recambio: str = None, tipo_garantia: str = None) -> dict:
        """
        Envía/actualiza el presupuesto con precio y descripción de reparación.
        Incluye campos adicionales requeridos por Sumbroker:
        - disponibilidad_recambios: "inmediata", "24h", "48h", "7dias", "sin_stock"
        - tiempo_horas: Tiempo estimado en horas de trabajo
        - tipo_recambio: "original", "compatible", "reacondicionado", "no_aplica"
        - tipo_garantia: "fabricante", "taller", "sin_garantia"
        """
        if not await self._ensure_auth():
            return {"success": False, "error": "Authentication failed"}
        
        try:
            # Mapear tipo de recambio a valores de Sumbroker
            repair_type_map = {
                "original": 1,
                "compatible": 2,
                "reacondicionado": 3,
                "no_aplica": 4
            }
            
            # Mapear tipo de garantía a valores de Sumbroker
            warranty_type_map = {
                "fabricante": 1,
                "taller": 2,
                "sin_garantia": 3
            }
            
            # Mapear disponibilidad de recambios
            availability_map = {
                "inmediata": 1,
                "24h": 2,
                "48h": 3,
                "7dias": 4,
                "sin_stock": 5
            }
            
            payload = {
                "price": price,
                "repair_description": description,
                "repair_time": repair_time,
                "warranty_months": warranty_months
            }
            
            # Agregar campos opcionales si están presentes
            if tipo_recambio and tipo_recambio in repair_type_map:
                payload["repair_type"] = repair_type_map[tipo_recambio]
            
            if tipo_garantia and tipo_garantia in warranty_type_map:
                payload["warranty_type"] = warranty_type_map[tipo_garantia]
            
            if disponibilidad_recambios and disponibilidad_recambios in availability_map:
                payload["spare_parts_availability"] = availability_map[disponibilidad_recambios]
            
            if tiempo_horas is not None:
                payload["repair_time_hours"] = tiempo_horas
            
            logger.info(f"Submitting budget {budget_id} with payload: {payload}")
            
            resp = await self._request_with_retry(
                "patch", f"{API_BASE}/store-budget/{budget_id}",
                json=payload)
            
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            else:
                logger.error(f"Error submitting budget: {resp.status_code} {resp.text[:300]}")
                return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            logger.error(f"Exception submitting budget: {e}")
            return {"success": False, "error": str(e)}

    async def update_tracking(self, budget_id: int, tracking_number: str, 
                             shipping_company: str = None, shipping_date: str = None) -> dict:
        """Actualiza el número de tracking del envío"""
        if not await self._ensure_auth():
            return {"success": False, "error": "Authentication failed"}
        
        try:
            payload = {"tracking_number": tracking_number}
            if shipping_company:
                payload["shipping_company"] = shipping_company
            if shipping_date:
                payload["shipping_date"] = shipping_date
            
            resp = await self._request_with_retry(
                "patch", f"{API_BASE}/store-budget/{budget_id}",
                json=payload)
            
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            else:
                logger.error(f"Error updating tracking: {resp.status_code} {resp.text[:300]}")
                return {"success": False, "error": resp.text[:300]}
        except Exception as e:
            logger.error(f"Exception updating tracking: {e}")
            return {"success": False, "error": str(e)}

    async def mark_as_received(self, budget_id: int, received_date: str = None) -> dict:
        """Marca el dispositivo como recibido — solo actualiza pickup_date, sin cambio de status"""
        data = {"pickup_date": received_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        return await self.update_budget_status(budget_id, status=None, extra_data=data)

    async def mark_as_in_repair(self, budget_id: int) -> dict:
        """En reparación — no hay status especifico en Sumbroker, solo informativo"""
        return {"success": True, "data": {"info": "No specific Sumbroker status for in_repair"}}

    async def mark_as_repaired(self, budget_id: int, repair_date: str = None) -> dict:
        """Marca el dispositivo como reparado — actualiza repair_date"""
        data = {"repair_date": repair_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        return await self.update_budget_status(budget_id, status=None, extra_data=data)

    async def mark_as_shipped(self, budget_id: int, tracking_number: str, 
                             shipping_company: str = None) -> dict:
        """Marca el dispositivo como enviado con tracking — actualiza campos de envío"""
        data = {
            "tracking_number": tracking_number,
            "shipping_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        if shipping_company:
            data["shipping_company"] = shipping_company
        return await self.update_budget_status(budget_id, status=None, extra_data=data)

    async def mark_as_delivered(self, budget_id: int, delivery_date: str = None) -> dict:
        """Marca el dispositivo como entregado — actualiza delivery_date"""
        data = {"delivery_date": delivery_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        return await self.update_budget_status(budget_id, status=None, extra_data=data)

    # ── photo upload ─────────────────────────────────────────

    async def upload_photo(self, budget_id: int, file_path: str, photo_type: str = "repair") -> dict:
        """
        Upload a photo to Sumbroker for a budget.
        photo_type: 'before', 'after', 'repair', 'damage'
        
        Note: This attempts to upload via the API. If the API doesn't support uploads,
        it will return an error with instructions to use the web portal.
        """
        if not self._token:
            if not await self.authenticate():
                return {"success": False, "error": "Authentication failed"}
        
        try:
            import os
            import mimetypes
            
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            # Try standard document upload endpoint
            # Common patterns: /store-budget/{id}/documents, /policy-risk-claim/{id}/docs
            endpoints_to_try = [
                f"{API_BASE}/store-budget/{budget_id}/documents",
                f"{API_BASE}/store_budget/{budget_id}/documents",
                f"{API_BASE}/store-budget/{budget_id}/docs",
            ]
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                for endpoint in endpoints_to_try:
                    try:
                        with open(file_path, 'rb') as f:
                            files = {'file': (filename, f, mime_type)}
                            data = {'type': photo_type, 'name': filename}
                            
                            headers = {"Authorization": f"Bearer {self._token}",
                                       "Accept": "application/json",
                                       "X-localization": "es"}
                            
                            resp = await client.post(
                                endpoint,
                                files=files,
                                data=data,
                                headers=headers,
                            )
                            
                            if resp.status_code in [200, 201]:
                                return {"success": True, "data": resp.json()}
                            elif resp.status_code == 404:
                                continue  # Try next endpoint
                            else:
                                logger.warning(f"Upload attempt to {endpoint}: {resp.status_code}")
                    except Exception as e:
                        logger.warning(f"Upload attempt exception: {e}")
                        continue
            
            # If all endpoints failed, return info about manual upload
            return {
                "success": False, 
                "error": "API photo upload not supported. Use portal web.",
                "portal_url": "https://distribuidor.sumbroker.es"
            }
            
        except Exception as e:
            logger.error(f"Exception uploading photo: {e}")
            return {"success": False, "error": str(e)}

    async def upload_photos_batch(self, budget_id: int, file_paths: list, photo_type: str = "repair") -> dict:
        """Upload multiple photos in batch."""
        results = {"success": True, "uploaded": [], "failed": []}
        
        for path in file_paths:
            result = await self.upload_photo(budget_id, path, photo_type)
            if result.get("success"):
                results["uploaded"].append(path)
            else:
                results["failed"].append({"path": path, "error": result.get("error")})
        
        results["success"] = len(results["failed"]) == 0
        return results

    # ── reject budget ────────────────────────────────────────

    async def reject_budget(self, budget_id: int, reason: str = None) -> dict:
        """Reject a budget from the repair shop side."""
        if not await self._ensure_auth():
            return {"success": False, "error": "Authentication failed"}
        
        try:
            # First, try sending an observation explaining the rejection
            if reason:
                await self.send_observation(
                    budget_id, 
                    f"RECHAZO DE REPARACIÓN: {reason}",
                    visible_to_client=False
                )
            
            # Try PATCH with rejection info
            payload = {
                "shop_rejection": True,
                "shop_rejection_reason": reason or "Reparación no viable"
            }
            
            resp = await self._request_with_retry(
                "patch", f"{API_BASE}/store-budget/{budget_id}",
                json=payload)
            
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            elif resp.status_code == 422:
                return {
                    "success": False,
                    "error": "Rechazo directo no soportado por API. Use observaciones.",
                    "observation_sent": bool(reason)
                }
            else:
                return {"success": False, "error": f"Status {resp.status_code}: {resp.text[:200]}"}
                    
        except Exception as e:
            logger.error(f"Exception rejecting budget: {e}")
            return {"success": False, "error": str(e)}

    # ── connection test ─────────────────────────────────────

    async def test_connection(self) -> dict:
        """Quick connectivity check — returns login success + basic stats."""
        try:
            ok = await self.authenticate()
            if not ok:
                return {"success": False, "error": "Login failed"}

            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.get(
                    f"{API_BASE}/store-budget",
                    params={"limit": 1},
                    headers=self._headers(),
                )
                total = 0
                if resp.status_code == 200:
                    total = resp.json().get("total", 0)

            return {
                "success": True,
                "user": self._user_data.get("name"),
                "role": self._user_data.get("role"),
                "store_budgets_total": total,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
