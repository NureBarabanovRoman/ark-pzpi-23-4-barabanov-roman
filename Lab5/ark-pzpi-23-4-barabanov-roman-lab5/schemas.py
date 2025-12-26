from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str = "user"

class UserRead(BaseModel):
    id: str
    email: str
    role: str
    class Config:
        from_attributes = True

class SystemLogRead(BaseModel):
    id: int
    user_email: str
    action: str
    details: Optional[str]
    timestamp: datetime
    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    role: str

class DeviceRegister(BaseModel):
    device_id: str
    device_type: str = "button"
    room_id: Optional[str] = None

class IoTClick(BaseModel):
    device_id: str
    button_index: int

class DeviceRead(BaseModel):
    id: str
    room_id: Optional[str]
    battery_level: int
    last_seen: datetime
    class Config:
        from_attributes = True

class OptionBase(BaseModel):
    text: str

class PollCreate(BaseModel):
    title: str
    description: Optional[str] = None
    room_id: str
    options: List[OptionBase]

class OptionRead(OptionBase):
    id: str
    vote_count: int
    class Config:
        from_attributes = True

class PollRead(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    room_id: str
    is_active: bool = True
    owner_id: Optional[str] = None
    options: List[OptionRead]
    class Config:
        from_attributes = True

class PollAnalytics(BaseModel):
    total_votes: int
    controversy_index: float
    consensus_status: str

class OptionReadWithStats(BaseModel):
    id: str
    text: str
    vote_count: int
    percentage: float
    margin_of_error: float

class PollReadDetailed(PollRead):
    analytics: PollAnalytics
    options: List[OptionReadWithStats]