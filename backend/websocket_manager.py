"""
WebSocket Manager para notificaciones en tiempo real
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime, timezone

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas"""
    
    def __init__(self):
        # Diccionario de conexiones por user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Conexiones de admin (reciben todas las notificaciones)
        self.admin_connections: List[WebSocket] = []
        # IDs de usuarios admin
        self.admin_user_ids: Set[str] = set()
    
    async def connect(self, websocket: WebSocket, user_id: str, role: str):
        """Conecta un nuevo cliente WebSocket"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Si es admin o master, añadir a lista de admins
        if role in ['admin', 'master']:
            self.admin_connections.append(websocket)
            self.admin_user_ids.add(user_id)
        
        print(f"[WS] Usuario {user_id} ({role}) conectado. Total conexiones: {sum(len(v) for v in self.active_connections.values())}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Desconecta un cliente WebSocket"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        
        print(f"[WS] Usuario {user_id} desconectado.")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Envía mensaje a un usuario específico"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WS] Error enviando a {user_id}: {e}")
    
    async def broadcast_to_admins(self, message: dict):
        """Envía mensaje a todos los admins conectados"""
        disconnected = []
        for connection in self.admin_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WS] Error en broadcast admin: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones muertas
        for conn in disconnected:
            if conn in self.admin_connections:
                self.admin_connections.remove(conn)
    
    async def broadcast_to_all(self, message: dict):
        """Envía mensaje a todos los usuarios conectados"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass
    
    async def notify_event(self, event_type: str, data: dict, target_user_id: str = None):
        """Notifica un evento con sonido opcional"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "play_sound": True
        }
        
        # Eventos que van a todos los admins
        admin_events = [
            "nueva_orden",
            "material_añadido",
            "mensaje_tecnico",
            "presupuesto_aceptado",
            "imei_no_coincide",
            "orden_bloqueada"
        ]
        
        if event_type in admin_events:
            await self.broadcast_to_admins(message)
        elif target_user_id:
            await self.send_personal_message(message, target_user_id)
        else:
            await self.broadcast_to_all(message)


# Instancia global del manager
ws_manager = ConnectionManager()


async def notify_new_notification(notification_data: dict, target_user_id: str = None):
    """Helper para notificar una nueva notificación desde cualquier parte del código"""
    await ws_manager.notify_event(
        event_type="nueva_notificacion",
        data=notification_data,
        target_user_id=target_user_id
    )


async def notify_incoming_call(call_data: dict):
    """Helper para notificar una llamada entrante"""
    await ws_manager.notify_event(
        event_type="llamada_entrante",
        data=call_data
    )
