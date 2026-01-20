"""
Configuration management for QR Research project.
Uses environment variables for sensitive data.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Twilio credentials
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

    # Claude API for classification
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    # Flask settings
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

    # Ngrok (for local development webhook exposure)
    NGROK_AUTH_TOKEN = os.getenv('NGROK_AUTH_TOKEN')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/qr_research.db')

    # Storage paths
    IMAGES_DIR = 'data/images'
    SCREENSHOTS_DIR = 'data/screenshots'

    # Browser settings
    BROWSER_TIMEOUT = 30  # seconds
    BROWSER_HEADLESS = True

    # Classification settings
    CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.7  # Below this, flag for manual review

    # Cost optimization
    SKIP_CLASSIFICATION_FOR_DUPLICATES = True  # Don't re-classify duplicate QR codes
    MAX_SCREENSHOT_SIZE = (1280, 720)  # Reduce storage costs

    @classmethod
    def validate(cls):
        """Check if required config values are set"""
        required = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_PHONE_NUMBER'
        ]
        missing = [key for key in required if not getattr(cls, key)]

        if missing:
            print(f"Warning: Missing required config: {', '.join(missing)}")
            return False
        return True

    @classmethod
    def is_classification_enabled(cls):
        """Check if AI classification is configured"""
        return bool(cls.ANTHROPIC_API_KEY)
