#!/usr/bin/env python3
"""
Performance Benchmark Script - Fase 1 Diagnóstico
Mide latencias reales de endpoints y queries críticos
"""
import asyncio
import time
import statistics
import httpx
import json
from datetime import datetime
from typing import List, Dict
import os

API_URL = os.environ.get("API_URL", "https://workshop-erp-3.preview.emergentagent.com")

# Test credentials
MASTER_EMAIL = "ramiraz91@gmail.com"
MASTER_PASS = "temp123"

async def login() -> str:
    """Get auth token"""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_URL}/api/auth/login", json={
            "email": MASTER_EMAIL,
            "password": MASTER_PASS
        })
        return r.json().get("token", "")

async def benchmark_endpoint(client: httpx.AsyncClient, endpoint: str, 
                             headers: dict, iterations: int = 10) -> Dict:
    """Benchmark a single endpoint"""
    latencies = []
    sizes = []
    errors = 0
    
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            r = await client.get(f"{API_URL}{endpoint}", headers=headers)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
            sizes.append(len(r.content))
            if r.status_code >= 400:
                errors += 1
        except Exception as e:
            errors += 1
            latencies.append(30000)  # Timeout marker
    
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    
    return {
        "endpoint": endpoint,
        "iterations": iterations,
        "errors": errors,
        "p50_ms": round(sorted_lat[int(n * 0.5)], 1),
        "p95_ms": round(sorted_lat[int(n * 0.95)] if n >= 20 else sorted_lat[-1], 1),
        "p99_ms": round(sorted_lat[-1], 1),
        "avg_ms": round(statistics.mean(latencies), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "avg_size_kb": round(statistics.mean(sizes) / 1024, 1) if sizes else 0,
    }

async def run_benchmark():
    """Run full benchmark suite"""
    print("=" * 80)
    print(f"BENCHMARK DE RENDIMIENTO - {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Login
    print("\n[1] Obteniendo token de autenticación...")
    token = await login()
    if not token:
        print("ERROR: No se pudo obtener token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Endpoints críticos a medir
    endpoints = [
        # Listados principales (los más lentos típicamente)
        "/api/ordenes",
        "/api/ordenes?estado=pendiente_recibir",
        "/api/ordenes?estado=en_taller",
        "/api/ordenes?estado=reparado",
        "/api/ordenes/dashboard-stats",
        
        # Búsquedas
        "/api/ordenes?search=OT-2026",
        "/api/clientes",
        "/api/clientes?search=test",
        
        # Catálogos
        "/api/repuestos",
        "/api/transportistas",
        
        # Detalle de orden (con ID real)
        "/api/ordenes/d146a59b-16d0-4f52-8c7b-607579064842",
        
        # Expedientes Insurama
        "/api/insurama/expedientes",
        
        # Admin / Logs
        "/api/admin/audit-logs?limit=50",
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=60) as client:
        print("\n[2] Ejecutando benchmark (10 iteraciones por endpoint)...\n")
        
        for endpoint in endpoints:
            print(f"  Midiendo: {endpoint[:60]}...", end=" ", flush=True)
            result = await benchmark_endpoint(client, endpoint, headers, iterations=10)
            results.append(result)
            
            # Indicador de velocidad
            p95 = result["p95_ms"]
            indicator = "🟢" if p95 < 200 else "🟡" if p95 < 500 else "🔴"
            print(f"{indicator} p95={p95}ms, size={result['avg_size_kb']}KB")
    
    # Ordenar por p95 descendente
    results.sort(key=lambda x: x["p95_ms"], reverse=True)
    
    # Imprimir reporte
    print("\n" + "=" * 100)
    print("RESULTADOS ORDENADOS POR LATENCIA (p95)")
    print("=" * 100)
    print(f"{'Endpoint':<55} {'p50':>7} {'p95':>7} {'p99':>7} {'Max':>7} {'Size':>8}")
    print("-" * 100)
    
    for r in results:
        p95 = r["p95_ms"]
        indicator = "🟢" if p95 < 200 else "🟡" if p95 < 500 else "🔴"
        print(f"{indicator} {r['endpoint']:<53} {r['p50_ms']:>6.0f}ms {r['p95_ms']:>6.0f}ms {r['p99_ms']:>6.0f}ms {r['max_ms']:>6.0f}ms {r['avg_size_kb']:>6.1f}KB")
    
    # Resumen
    print("\n" + "=" * 100)
    print("RESUMEN")
    print("=" * 100)
    slow_endpoints = [r for r in results if r["p95_ms"] > 500]
    medium_endpoints = [r for r in results if 200 < r["p95_ms"] <= 500]
    fast_endpoints = [r for r in results if r["p95_ms"] <= 200]
    
    print(f"🔴 Endpoints lentos (>500ms p95): {len(slow_endpoints)}")
    for e in slow_endpoints:
        print(f"   - {e['endpoint']}: {e['p95_ms']}ms")
    
    print(f"🟡 Endpoints medios (200-500ms p95): {len(medium_endpoints)}")
    print(f"🟢 Endpoints rápidos (<200ms p95): {len(fast_endpoints)}")
    
    # Guardar resultados
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_url": API_URL,
        "results": results,
        "summary": {
            "total_endpoints": len(results),
            "slow_count": len(slow_endpoints),
            "medium_count": len(medium_endpoints),
            "fast_count": len(fast_endpoints)
        }
    }
    
    with open("/app/backend/benchmark_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Resultados guardados en /app/backend/benchmark_results.json")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_benchmark())
