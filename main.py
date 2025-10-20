from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid
import json
import random
from typing import Dict, List, Set, Optional

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Store active connections
class ConnectionManager:
    def __init__(self):
        # All active connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Waiting for match
        self.waiting_text: Dict[str, Set[str]] = {}  # interest -> set of connection_ids
        self.waiting_video: Dict[str, Set[str]] = {}  # interest -> set of connection_ids
        # Matched pairs
        self.matches: Dict[str, str] = {}  # connection_id -> partner_connection_id

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        # Broadcast updated online count
        await self.broadcast_online_count()
        return connection_id

    def disconnect(self, connection_id: str):
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from waiting lists
        for interest, connections in self.waiting_text.items():
            if connection_id in connections:
                connections.remove(connection_id)
        
        for interest, connections in self.waiting_video.items():
            if connection_id in connections:
                connections.remove(connection_id)
        
        # Handle disconnection from a match
        if connection_id in self.matches:
            partner_id = self.matches[connection_id]
            # Inform partner about disconnection
            if partner_id in self.active_connections:
                asyncio.create_task(self.send_personal_message(
                    {"type": "system", "message": "Your chat partner has disconnected."},
                    partner_id
                ))
            # Remove both from matches
            if connection_id in self.matches:
                del self.matches[connection_id]
            if partner_id in self.matches:
                del self.matches[partner_id]
        
        # Broadcast updated online count
        asyncio.create_task(self.broadcast_online_count())

    async def find_match(self, connection_id: str, chat_type: str, interests: List[str]):
        # Default interest if none provided
        if not interests:
            interests = ["general"]
        
        waiting_dict = self.waiting_text if chat_type == "text" else self.waiting_video
        
        # Try to find a match with similar interests
        for interest in interests:
            if interest in waiting_dict and waiting_dict[interest]:
                # Get a random match from the waiting pool with the same interest
                match_candidates = list(waiting_dict[interest])
                if match_candidates:
                    partner_id = random.choice(match_candidates)
                    waiting_dict[interest].remove(partner_id)
                    
                    # Create the match
                    self.matches[connection_id] = partner_id
                    self.matches[partner_id] = connection_id
                    
                    return partner_id
        
        # If no match found, add to waiting list
        for interest in interests:
            if interest not in waiting_dict:
                waiting_dict[interest] = set()
            waiting_dict[interest].add(connection_id)
        
        return None

    async def send_personal_message(self, message, connection_id: str):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(message)
    
    async def broadcast_online_count(self):
        online = len(self.active_connections)
        for conn_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_json({"type": "online", "count": online})
            except Exception:
                # Ignore failures; best-effort broadcast
                pass

manager = ConnectionManager()

import asyncio

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video-chat", response_class=HTMLResponse)
async def get_video_chat(request: Request):
    return templates.TemplateResponse("video_chat.html", {"request": request})

@app.get("/text-chat", response_class=HTMLResponse)
async def get_text_chat(request: Request):
    return templates.TemplateResponse("text_chat.html", {"request": request})

@app.websocket("/ws/{chat_type}")
async def websocket_endpoint(websocket: WebSocket, chat_type: str):
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, connection_id)
    
    try:
        # Wait for initial message with interests
        data = await websocket.receive_json()
        interests = data.get("interests", [])
        
        # Find a match
        partner_id = await manager.find_match(connection_id, chat_type, interests)
        
        if partner_id:
            # Inform both users they've been matched
            await manager.send_personal_message(
                {"type": "system", "message": "You've been connected to a stranger!"},
                connection_id
            )
            await manager.send_personal_message(
                {"type": "system", "message": "You've been connected to a stranger!"},
                partner_id
            )
        else:
            await manager.send_personal_message(
                {"type": "system", "message": "Waiting for someone to connect..."},
                connection_id
            )
        
        # Main message loop
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data["type"] == "message":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "message", "message": data["message"]},
                        partner_id
                    )
            
            elif data["type"] == "typing":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "typing", "isTyping": data["isTyping"]},
                        partner_id
                    )
            
            elif data["type"] == "video-signal":
                if connection_id in manager.matches:
                    partner_id = manager.matches[connection_id]
                    await manager.send_personal_message(
                        {"type": "video-signal", "signal": data["signal"]},
                        partner_id
                    )
            
            elif data["type"] == "find-new":
                # Remove from current match
                if connection_id in manager.matches:
                    old_partner_id = manager.matches[connection_id]
                    if old_partner_id in manager.matches:
                        del manager.matches[old_partner_id]
                    del manager.matches[connection_id]
                    
                    # Inform old partner
                    await manager.send_personal_message(
                        {"type": "system", "message": "Your chat partner has disconnected."},
                        old_partner_id
                    )
                
                # Find a new match
                interests = data.get("interests", [])
                new_partner_id = await manager.find_match(connection_id, chat_type, interests)
                
                if new_partner_id:
                    # Inform both users they've been matched
                    await manager.send_personal_message(
                        {"type": "system", "message": "You've been connected to a new stranger!"},
                        connection_id
                    )
                    await manager.send_personal_message(
                        {"type": "system", "message": "You've been connected to a stranger!"},
                        new_partner_id
                    )
                else:
                    await manager.send_personal_message(
                        {"type": "system", "message": "Waiting for someone to connect..."},
                        connection_id
                    )
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(connection_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)