from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.deps import get_auth_service

from src.service.auth import AuthService
from src.schemas.user import UserCreate, UserResponse, Token


router = APIRouter(prefix="/auth", tags=["auth"])

#may need to replace token location in the new file schemas/token.py
@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.register(user)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.login(user_data=form_data)