import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.db.mongo import log_error
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from jose import jwt 
from datetime import datetime, timedelta
from app.core.config import settings

async def handle_validation_error(request: Request, exc: RequestValidationError):
    """Handle validation errors and log them to MongoDB"""
    await log_error(
        error=exc,
        location="request_validation",
        additional_info={
            "path": request.url.path,
            "method": request.method,
            "validation_errors": exc.errors()
        }
    )
    raise HTTPException(status_code=422, detail=str(exc))

async def send_password_email(email: str, password: str) -> bool:
    """
    Send a password email to the user.
    
    Args:
        email: The recipient's email address
        password: The generated password to send
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = settings.EMAIL_FROM
        message["To"] = email
        message["Subject"] = "Your Login Password"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Your Login Password</h2>
            <p>Thank you for using our service. Here's your password:</p>
            <h3 style="background-color: #f2f2f2; padding: 10px; font-family: monospace;">{password}</h3>
            <p>This password will expire in 72 hours.</p>
            <p>If you didn't request this password, please ignore this email.</p>
        </body>
        </html>
        """
        
        # Attach the body to the message
        message.attach(MIMEText(body, "html"))
        
        # Connect to the SMTP server
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            # Start TLS for security
            server.starttls()
            
            # Login to the email server
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            
            # Send the email
            server.send_message(message)
            
        print(f"Password email sent successfully to {email}")
        return True
        
    except Exception as e:
        # Log the error to MongoDB
        await log_error(
            error=e,
            location="send_password_email",
            additional_info={"email": email}
        )
        print(f"Failed to send password email to {email}: {str(e)}")
        return False

async def create_access_token(data: dict)->str:
    """
    Create an JWT access token which expires in 1 hour
    
    Args:
        data: The data to encode in the token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRY_SECONDS)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def create_refresh_token(data: dict)->str:
    """
    Create a JWT refresh token which expires in 3 days
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRY_SECONDS)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt



