"""
Revix · Módulo de Agentes IA (nativos).

Orquestador multi-agente que usa Claude Sonnet 4.5 con tool-calling
y ejecuta tools a través del servidor MCP interno (runtime).

Agentes disponibles (Fase 1, solo lectura):
  - kpi_analyst        · Análisis de negocio y métricas
  - auditor            · Auditoría transversal + ISO 9001
  - seguimiento_publico · Asistente al cliente final (solo token)
"""
