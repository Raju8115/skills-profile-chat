"""
Configuration file for Chat Assist Service
Loads environment variables for database and Watsonx.ai connections
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for Chat Assist service"""
    
    # Database Configuration
    DB2_USERNAME = os.getenv("DB2_USERNAME")
    DB2_PASSWORD = os.getenv("DB2_PASSWORD")
    DB2_HOSTNAME = os.getenv("DB2_HOSTNAME")
    DB2_PORT = os.getenv("DB2_PORT", "30756")
    DB2_DATABASE = os.getenv("DB2_DATABASE", "bludb")
    DB2_SCHEMA = os.getenv("DB2_SCHEMA", "")
    
    # Watsonx.ai Configuration
    WATSONX_URL = os.getenv("WATSONX_URL")
    WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
    WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
    WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID")
    # WATSONX_URL = os.getenv("WATSONX_URL", "https://au-syd.ml.cloud.ibm.com")
    # WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "vMFIDIhzXgPKtX7G_-hNqVrt0BdXLXrz4pACbkVaww_C")
    # WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "2b41d077-7711-4655-b379-1b40cfaf4674")
    # WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "ibm/llama-3-3-70b-instruct")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8085"))
    API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # CORS Configuration
    CORS_ORIGINS = ["*"]  # Configure as needed for production
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        required_db_vars = [
            "DB2_USERNAME",
            "DB2_PASSWORD", 
            "DB2_HOSTNAME",
            "DB2_PORT",
            "DB2_DATABASE"
        ]
        
        required_watsonx_vars = [
            "WATSONX_URL",
            "WATSONX_API_KEY",
            "WATSONX_PROJECT_ID",
            "WATSONX_MODEL_ID"
        ]
        
        missing_vars = []
        
        for var in required_db_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        for var in required_watsonx_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please check your .env file in the project root."
            )
        
        return True
    
    @classmethod
    def get_db_connection_string(cls):
        """Get DB2 connection string"""
        return (
            f"DATABASE={cls.DB2_DATABASE};"
            f"HOSTNAME={cls.DB2_HOSTNAME};"
            f"PORT={cls.DB2_PORT};"
            f"PROTOCOL=TCPIP;"
            f"UID={cls.DB2_USERNAME};"
            f"PWD={cls.DB2_PASSWORD};"
            f"SECURITY=SSL;"
        )
    
    @classmethod
    def print_config(cls):
        """Print configuration (without sensitive data)"""
        print("=" * 60)
        print("Chat Assist Service Configuration")
        print("=" * 60)
        print(f"Database: {cls.DB2_DATABASE}")
        print(f"DB Host: {cls.DB2_HOSTNAME}")
        print(f"DB Port: {cls.DB2_PORT}")
        print(f"DB Schema: {cls.DB2_SCHEMA or 'Not specified'}")
        print(f"Watsonx URL: {cls.WATSONX_URL}")
        print(f"Watsonx Model: {cls.WATSONX_MODEL_ID}")
        print(f"API Host: {cls.API_HOST}")
        print(f"API Port: {cls.API_PORT}")
        print("=" * 60)


# Validate configuration on import
try:
    Config.validate()
    print("✅ Configuration validated successfully")
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    raise

# Made with Bob
