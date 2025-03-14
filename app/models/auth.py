from pydantic import BaseModel
from typing import List

class UserBase(BaseModel):
    email: str
    username: str
    full_name: str = None

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_approved: bool
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse] 