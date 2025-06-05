import boto3
import psycopg2
import json
import base64
import logging
from datetime import datetime
from typing import List, Dict, Tuple
from PIL import Image
from io import BytesIO
import tempfile
import os

from config import (
    S3_BUCKET_NAME, S3_FOLDER_PREFIX, S3_REGION,
    DB_CONFIG, DB_TABLE,
    BEDROCK_REGION, EMBEDDING_MODEL, EMBEDDING_DIMENSION
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=S3_REGION)
bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)

def create_s3_folder() -> str:
    """
    Create timestamped S3 folder
    
    Returns:
        folder_path: S3 folder path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_path = f"{S3_FOLDER_PREFIX}_{timestamp}/"
    
    logger.info(f"Created S3 folder path: {folder_path}")
    return folder_path

def upload_file_to_s3(file_obj, folder_path: str, filename: str) -> str:
    """
    Upload file to S3
    
    Returns:
        s3_url: Full S3 URL
    """
    try:
        s3_key = f"{folder_path}{filename}"
        
        # Reset file pointer
        file_obj.seek(0)
        
        # Upload to S3
        s3_client.upload_fileobj(
            file_obj, 
            S3_BUCKET_NAME, 
            s3_key,
            ExtraArgs={'ContentType': 'application/octet-stream'}
        )
        
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"✅ Uploaded to S3: {filename}")
        
        return s3_url
        
    except Exception as e:
        logger.error(f"❌ S3 upload failed for {filename}: {str(e)}")
        raise

def generate_image_embedding(image_bytes: bytes) -> Tuple[List[float], str]:
    """
    Generate embedding for image using AWS Bedrock Titan
    
    Returns:
        (embedding_vector, base64_image)
    """
    try:
        # Convert to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare request payload
        payload = {
            "inputImage": base64_image,
            "embeddingConfig": {
                "outputEmbeddingLength": EMBEDDING_DIMENSION
            }
        }
        
        # Call Bedrock API
        response = bedrock_client.invoke_model(
            body=json.dumps(payload),
            modelId=EMBEDDING_MODEL,
            accept="application/json",
            contentType="application/json"
        )
        
        # Parse response
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        
        if not embedding:
            raise ValueError("No embedding returned from Bedrock")
        
        logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
        return embedding, base64_image
        
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {str(e)}")
        raise

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise

def insert_record_to_db(conn, record: Dict) -> bool:
    """
    Insert record to PostgreSQL database
    
    Args:
        conn: Database connection
        record: Dict with keys: image_name, embedding, image_base64, description, s3_url
    
    Returns:
        success: Boolean
    """
    try:
        cursor = conn.cursor()
        
        insert_query = f"""
            INSERT INTO {DB_TABLE} (image_name, embedding, image_base64, description, s3_url)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            record['image_name'],
            record['embedding'],
            record['image_base64'],
            record['description'],
            record['s3_url']
        ))
        
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Inserted to DB: {record['image_name']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ DB insertion failed for {record['image_name']}: {str(e)}")
        conn.rollback()
        return False

def process_image_record(record: Dict, s3_folder: str) -> Tuple[bool, str]:
    """
    Process single image record: generate embedding, upload to S3, insert to DB
    
    Args:
        record: Dict with image_name, description, image_file
        s3_folder: S3 folder path
    
    Returns:
        (success, error_message)
    """
    try:
        image_name = record['image_name']
        description = record['description']
        image_file = record['image_file']
        
        logger.info(f"🔄 Processing: {image_name}")
        
        # Get image bytes
        image_file.seek(0)
        image_bytes = image_file.getvalue()
        
        # Generate embedding
        embedding, base64_image = generate_image_embedding(image_bytes)
        
        # Upload image to S3
        image_filename = f"{image_name}.jpg"
        image_file.seek(0)  # Reset pointer
        s3_url = upload_file_to_s3(image_file, s3_folder, image_filename)
        
        # Prepare database record
        db_record = {
            'image_name': image_name,
            'embedding': embedding,
            'image_base64': base64_image,
            'description': description,
            's3_url': s3_url
        }
        
        # Insert to database
        conn = get_db_connection()
        success = insert_record_to_db(conn, db_record)
        conn.close()
        
        if success:
            logger.info(f"✅ Successfully processed: {image_name}")
            return True, "Success"
        else:
            return False, "Database insertion failed"
            
    except Exception as e:
        error_msg = f"Processing failed for {record.get('image_name', 'unknown')}: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return False, error_msg

def upload_csv_to_s3(csv_file, s3_folder: str, filename: str = "descriptions.csv") -> str:
    """
    Upload CSV file to S3
    
    Returns:
        s3_url: Full S3 URL for CSV
    """
    try:
        csv_file.seek(0)  # Reset file pointer
        s3_url = upload_file_to_s3(csv_file, s3_folder, filename)
        logger.info(f"✅ CSV uploaded to S3: {filename}")
        return s3_url
        
    except Exception as e:
        logger.error(f"❌ CSV upload to S3 failed: {str(e)}")
        raise


