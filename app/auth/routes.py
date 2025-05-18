from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Response, Request
from app.auth.schemas import EmailRequest, LoginResponse, User, PasswordVerifyRequest
from app.db.mongo import get_db, log_error
from pymongo.database import Database
import random
import string
from app.auth.utils import send_password_email, create_access_token, create_refresh_token
from app.core.config import settings
from jose import JWTError, jwt

router = APIRouter()

@router.post("/request-login", response_model=LoginResponse)
async def request_login(
    request: EmailRequest, 
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """
    Route to handle initial login email submission.
    Takes an email from the request body, generates a password with 72-hour expiry,
    stores it in the database, and sends it via email.
    """
    try:
        email = request.email

        # Generate a random password (6 characters)
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # Set current time and expiry time (72 hours from now)
        current_time = datetime.utcnow()
        password_expiry = current_time + timedelta(hours=72)

        # Get the users collection
        users_collection = db["users"]
        
        # Check if the user already exists
        existing_user = await users_collection.find_one({"email": email})
        
        if existing_user:
            # Update the existing user's password and expiry
            await users_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "password": password,
                        "password_expiry": password_expiry,
                        "updated_at": current_time
                    }
                }
            )
        else:
            # Create a new user with password expiry
            new_user = {
                "email": email,
                "password": password,
                "password_expiry": password_expiry,
                "created_at": current_time,
                "updated_at": current_time,
                "no_of_csv_files_daily_limit": 1
            }
            await users_collection.insert_one(new_user)

        # Add the email sending task directly to background_tasks
        background_tasks.add_task(send_password_email, email, password)
        
        # Return a properly structured response
        return LoginResponse(
            message="Login instructions are being sent to your email",
            success=True,
            email=email
        )
    
    except Exception as e:
        # Log the error to MongoDB
        await log_error(
            error=e,
            location="request_login",
            additional_info={"email": request.email}
        )
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/verify-password")
async def verify_password(
    request: PasswordVerifyRequest,
    response: Response,
    db: Database = Depends(get_db)
):
    try:
        users_collection = db["users"]
        user = await users_collection.find_one({"email": request.email})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user["password"] != request.password:
            raise HTTPException(status_code=401, detail="Invalid password")

        if datetime.utcnow() > user["password_expiry"]:
            raise HTTPException(status_code=401, detail="Password has expired. Please request a new one.")

        #Generate tokens
        access_token = await create_access_token({"email": user["email"]})
        refresh_token = await create_refresh_token({"email": user["email"]})

        #Set refresh token in secure HttpOnly cookie (This is a secure cookie that cannot be accessed by JavaScript)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRY_SECONDS,
            path="/refresh-token"
        )

        #Return the access token in response
        return {
            "message": "Password verified successfully",
            "success": True,
            "email": request.email,
            "access_token": access_token
        }

    except Exception as e:
        await log_error(error=e, location="verify_password", additional_info={"email": request.email})
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@router.post("/refresh-token")
async def refresh_token(request: Request, response: Response):
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

         #This helps us to verify the refresh token is signed by the JWT_SECRET_KEY and the algorithm is the one we are using
        payload = jwt.decode(   
            refresh_token, 
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Create new tokens
        new_access_token = await create_access_token({"email": email})
        new_refresh_token = await create_refresh_token({"email": email})  # Rotate if you want

        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=settings.REFRESH_TOKEN_EXPIRY_SECONDS,
            path="/refresh-token"
        )

        # Return new access token
        return {
            "access_token": new_access_token,
            "success": True,
            "message": "Token refreshed successfully"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    except Exception as e:
        await log_error(error=e, location="refresh_token", additional_info={})
        raise HTTPException(status_code=500, detail="An error occurred")