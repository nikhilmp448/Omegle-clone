from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    chat_type: str
    interests: Optional[List[str]] = []


class MessageRequest(BaseModel):
    connection_id: str
    message: str


class TypingRequest(BaseModel):
    connection_id: str
    isTyping: bool


class VideoSignalRequest(BaseModel):
    connection_id: str
    signal: Dict[str, Any]


class FindNewRequest(BaseModel):
    connection_id: str
    interests: Optional[List[str]] = []
