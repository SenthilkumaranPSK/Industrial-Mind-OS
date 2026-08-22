from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from db.supabase_client import supabase
from . import auth_schemas

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Validate the Supabase JWT and return the user.
    """
    try:
        # Supabase client handles the JWT validation via get_user
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # We can extract metadata like username from user_metadata
        user_data = response.user
        return {
            "id": user_data.id,
            "email": user_data.email,
            "username": user_data.user_metadata.get("username", user_data.email.split("@")[0])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=auth_schemas.UserResponse)
def register_user(user: auth_schemas.UserCreate):
    try:
        # Sign up with Supabase
        # We store the username in user_metadata
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {"username": user.username}
            }
        })
        
        if not response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
            
        return {
            "id": response.user.id,
            "email": response.user.email,
            "username": user.username
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=auth_schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Sign in with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": form_data.username, # Supabase usually takes email for login
            "password": form_data.password
        })
        
        if not response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        return {
            "access_token": response.session.access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        # If user tried to login with username, we might need a lookup, 
        # but Supabase Auth natively prefers Email.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
