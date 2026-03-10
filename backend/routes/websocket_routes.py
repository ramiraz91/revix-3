"""
WebSocket routes para notificaciones en tiempo real
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt
from config import JWT_SECRET, JWT_ALGORITHM, db
from websocket_manager import ws_manager

router = APIRouter()

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(None)
):
    """
    WebSocket endpoint para recibir notificaciones en tiempo real.
    Requiere token JWT como query parameter.
    """
    user_id = None
    role = None
    
    try:
        # Validar token
        if not token:
            await websocket.close(code=4001, reason="Token requerido")
            return
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("user_id")
            role = payload.get("role")
        except jwt.ExpiredSignatureError:
            await websocket.close(code=4002, reason="Token expirado")
            return
        except jwt.InvalidTokenError:
            await websocket.close(code=4003, reason="Token inválido")
            return
        
        if not user_id:
            await websocket.close(code=4004, reason="Usuario no identificado")
            return
        
        # Conectar
        await ws_manager.connect(websocket, user_id, role)
        
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "type": "connected",
            "message": "Conectado al servidor de notificaciones",
            "user_id": user_id,
            "role": role
        })
        
        # Mantener conexión abierta y escuchar mensajes
        while True:
            try:
                # Esperar mensajes del cliente (heartbeat, etc.)
                data = await websocket.receive_text()
                
                # Responder a ping con pong
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"[WS] Error en conexión: {e}")
    finally:
        if user_id:
            ws_manager.disconnect(websocket, user_id)


@router.get("/api/ws/test")
async def test_websocket_broadcast():
    """Endpoint de prueba para enviar notificación de test"""
    await ws_manager.notify_event(
        event_type="test",
        data={"message": "Notificación de prueba"}
    )
    return {"message": "Notificación enviada"}
