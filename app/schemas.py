from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

class UserCreate(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
