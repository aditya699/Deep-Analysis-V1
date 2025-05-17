import pytest
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.utils import send_password_email
from core.config import settings

def test_email_configuration():
    """Test that email configuration variables are set"""
    assert settings.EMAIL_HOST, "EMAIL_HOST is not set"
    assert settings.EMAIL_PORT, "EMAIL_PORT is not set"
    assert settings.EMAIL_USERNAME, "EMAIL_USERNAME is not set"
    assert settings.EMAIL_PASSWORD, "EMAIL_PASSWORD is not set"
    assert settings.EMAIL_FROM, "EMAIL_FROM is not set"
    
    print(f"Email configuration is valid:")
    print(f"  HOST: {settings.EMAIL_HOST}")
    print(f"  PORT: {settings.EMAIL_PORT}")
    print(f"  USERNAME: {settings.EMAIL_USERNAME}")
    print(f"  FROM: {settings.EMAIL_FROM}")
    # Not printing password for security reasons

@pytest.mark.asyncio
async def test_send_test_email():
    """Test sending an actual email"""
    recipient = "meenakshi.bhtt@gmail.com"
    test_password = "TEST123"
    
    print(f"Sending test email to {recipient}...")
    result = await send_password_email(recipient, test_password)
    
    assert result is True, "Email sending failed"
    print("Test email sent successfully!")