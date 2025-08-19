# =============================================================================
# CONFIGURATION FILE - PLANOGRAM COMPLIANCE REVIEW
# =============================================================================
 
# S3 Configuration
S3_BUCKET_NAME = ""        # CHANGE THIS
S3_REGION = ""             # CHANGE THIS
S3_UPLOAD_FOLDER_PREFIX = "test_images"  # CHANGE THIS - folder prefix for uploaded images
 
# PostgreSQL Database Configuration
DB_CONFIG = {
    "host": "",
    "port": 5432,
    "database": "",
    "user": "",            # CHANGE THIS
    "password": "",        # CHANGE THIS
}
 
# Table Configuration
DB_RESULT = ""             # CHANGE THIS - results table name

# Label Studio Configuration
LABEL_STUDIO_API_TOKEN = ""     # CHANGE THIS
LABEL_STUDIO_BASE_URL = ""      # CHANGE THIS  
LABEL_STUDIO_PROJECT_ID = ""    # CHANGE THIS - ID của project để sync image vào

# Logging Configuration
LOG_LEVEL = "INFO"