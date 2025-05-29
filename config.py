# =============================================================================
# CONFIGURATION FILE - EASY TO EDIT
# =============================================================================

# S3 Configuration
S3_BUCKET_NAME = "uniben-data"  # CHANGE THIS
S3_FOLDER_PREFIX = "RAG_Update"  # Folder naming: RAG_Update_<timestamp>
S3_REGION = "ap-south-1"

# PostgreSQL Database Configuration
DB_CONFIG = {
    "host": "planogram-rag-test-db-01.cbgwyeimwp49.ap-southeast-1.rds.amazonaws.com",
    "port": 5432,
    "database": "planogramdb",
    "user": "postgres",      # CHANGE THIS
    "password": "Postgres123",  # CHANGE THIS
}

# Table Configuration
DB_TABLE = "embeddings"

# AWS Bedrock Configuration
BEDROCK_REGION = "ap-south-1"  # Region for Titan embedding model
EMBEDDING_MODEL = "amazon.titan-embed-image-v1"
EMBEDDING_DIMENSION = 1024

# File Processing Configuration
SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg']
MAX_FILE_SIZE_MB = 200
CSV_ENCODING = 'utf-8'

# Logging Configuration
LOG_LEVEL = "INFO"