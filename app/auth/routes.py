from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.auth.schemas import EmailRequest, LoginResponse, User
from app.db.mongo import get_db, log_error
from pymongo.database import Database
from fastapi import Depends
import random
import string
from app.auth.utils import send_password_email

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
            message="Login instructions sent to your email",
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