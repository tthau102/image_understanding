# =============================================================================
# CONFIGURATION FILE - EASY TO EDIT
# =============================================================================

# S3 Configuration
S3_BUCKET_NAME = ""  # CHANGE THIS
S3_FOLDER_PREFIX = ""  # Folder naming: RAG_Update_<timestamp>
S3_REGION = ""

# PostgreSQL Database Configuration
DB_CONFIG = {
    "host": "",
    "port": 5432,
    "database": "",
    "user": "",      # CHANGE THIS
    "password": "",  # CHANGE THIS
}

# Table Configuration
DB_TABLE = ""

# AWS Bedrock Configuration
BEDROCK_REGION = ""  # Region for Titan embedding model
EMBEDDING_MODEL = ""
EMBEDDING_DIMENSION = 1024

# File Processing Configuration
SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg']
MAX_FILE_SIZE_MB = 200
CSV_ENCODING = 'utf-8'

# Logging Configuration
LOG_LEVEL = "INFO"
LABEL_STUDIO_API_TOKEN = ""