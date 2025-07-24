"""
Database and storage operations for Planogram Compliance application.
Handles database connections, S3 operations, and review data management.
"""
import boto3
import psycopg2
import logging
from datetime import datetime
from typing import List, Dict, Optional
from app.config import config

# Setup logging
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations"""
    
    @staticmethod
    def get_connection():
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            logger.info("✅ Connected to PostgreSQL database")
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise
    
    @staticmethod
    def get_pending_review_items(conn) -> List[Dict]:
        """
        Get all pending review items from results table
        
        Args:
            conn: Database connection
            
        Returns:
            List of dictionaries containing pending review data
        """
        try:
            cursor = conn.cursor()
            
            query = f"""
                SELECT id, image_name, s3_url, product_count, compliance_assessment, 
                       review_comment, timestamp
                FROM {config.DB_RESULT_TABLE}
                ORDER BY timestamp DESC
            """
            cursor.execute(query)
            
            pending_items = []
            for row in cursor.fetchall():
                pending_items.append({
                    'id': row[0],
                    'image_name': row[1],
                    's3_url': row[2],
                    'product_count': row[3],
                    'compliance_assessment': row[4],
                    'review_comment': row[5] or '',
                    'timestamp': row[6]
                })
            
            cursor.close()
            logger.info(f"🔍 Found {len(pending_items)} pending review items")
            return pending_items
            
        except Exception as e:
            logger.error(f"❌ Failed to get pending review items: {str(e)}")
            return []


class S3Service:
    """Service for S3 operations"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3', 
            region_name=config.S3_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
        )
    
    def create_project_folder(self, project_id: int) -> str:
        """
        Create S3 folder for a specific Label Studio project
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            folder_path: S3 folder path for the project
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_path = f"{config.S3_FOLDER_PREFIX}-{project_id}/images_{timestamp}/"
        
        logger.info(f"Created S3 folder path: {folder_path}")
        return folder_path
    
    def upload_image_to_s3(self, image_file, folder_path: str, filename: str) -> str:
        """
        Upload image file to S3
        
        Args:
            image_file: Streamlit uploaded file object
            folder_path: S3 folder path  
            filename: Target filename
            
        Returns:
            s3_url: Full S3 URL
        """
        try:
            s3_key = f"{folder_path}{filename}"
            
            # Reset file pointer
            image_file.seek(0)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                image_file, 
                config.S3_BUCKET_NAME, 
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'private'  # Secure by default
                }
            )
            
            s3_url = f"https://{config.S3_BUCKET_NAME}.s3.{config.S3_REGION}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Uploaded to S3: {filename}")
            
            return s3_url
            
        except Exception as e:
            logger.error(f"❌ S3 upload failed for {filename}: {str(e)}")
            raise
    
    def generate_presigned_url(self, s3_url: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for S3 object
        
        Args:
            s3_url: Original S3 URL
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            presigned_url: Presigned URL for accessing the S3 object
        """
        try:
            # Extract bucket and key from S3 URL
            if not s3_url or not s3_url.startswith('https://'):
                return s3_url
            
            # Parse S3 URL to extract bucket and key
            url_parts = s3_url.replace('https://', '').split('/')
            bucket_part = url_parts[0]  # bucket-name.s3.region.amazonaws.com
            key = '/'.join(url_parts[1:])  # path/to/object
            
            # Extract bucket name (everything before .s3.)
            bucket_name = bucket_part.split('.s3.')[0]
            
            # Generate presigned URL
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            
            logger.info(f"✅ Generated presigned URL for: {key}")
            return presigned_url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL for {s3_url}: {str(e)}")
            # Return original URL as fallback
            return s3_url
    
    def upload_images_batch(self, uploaded_images: List, project_id: int) -> Dict:
        """
        Upload multiple images to S3 for a Label Studio project
        
        Args:
            uploaded_images: List of Streamlit uploaded file objects
            project_id: Label Studio project ID
            
        Returns:
            results: Dict with success/failure counts and details
        """
        results = {
            'total_images': len(uploaded_images),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'uploaded_files': [],
            's3_folder': '',
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Create project-specific folder
            s3_folder = self.create_project_folder(project_id)
            results['s3_folder'] = s3_folder
            
            logger.info(f"🚀 Starting batch upload of {len(uploaded_images)} images...")
            
            for i, image_file in enumerate(uploaded_images, 1):
                try:
                    # Generate filename
                    original_name = image_file.name
                    filename = f"image_{i:04d}_{original_name}"
                    
                    # Upload to S3
                    s3_url = self.upload_image_to_s3(image_file, s3_folder, filename)
                    
                    results['successful'] += 1
                    results['uploaded_files'].append({
                        'filename': filename,
                        'original_name': original_name,
                        's3_url': s3_url
                    })
                    
                    logger.info(f"✅ [{i}/{len(uploaded_images)}] Uploaded: {filename}")
                    
                except Exception as e:
                    results['failed'] += 1
                    error_msg = f"{image_file.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(f"❌ [{i}/{len(uploaded_images)}] Failed: {error_msg}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            results['processing_time'] = round(processing_time, 2)
            
            logger.info(f"🏁 Batch upload completed: {results['successful']}/{results['total_images']} successful")
            
            return results
            
        except Exception as e:
            error_msg = f"Batch upload failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results


class LambdaService:
    """Service for AWS Lambda operations"""
    
    def __init__(self):
        self.lambda_client = boto3.client(
            'lambda', 
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
        )
    
    def trigger_export_labels(self, project_id: int) -> Dict:
        """
        Trigger Lambda function to export labels from Label Studio
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            result: Dict with success status and response
        """
        try:
            logger.info(f"🚀 Triggering label export for project {project_id}")
            
            response = self.lambda_client.invoke(
                FunctionName=config.LAMBDA_FUNCTION_NAME,
                InvocationType='RequestResponse',
                Payload=f'{{"project_id": {project_id}}}'
            )
            
            # Parse response
            payload = response['Payload'].read().decode('utf-8')
            status_code = response['StatusCode']
            
            if status_code == 200:
                logger.info(f"✅ Lambda export completed for project {project_id}")
                return {
                    'success': True,
                    'status_code': status_code,
                    'response': payload
                }
            else:
                logger.error(f"❌ Lambda export failed with status {status_code}")
                return {
                    'success': False,
                    'status_code': status_code,
                    'response': payload
                }
                
        except Exception as e:
            error_msg = f"Lambda invoke failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }


# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection - convenience function"""
    return DatabaseService.get_connection()

def get_pending_review_items(conn) -> List[Dict]:
    """Get pending review items - convenience function"""
    return DatabaseService.get_pending_review_items(conn)

def generate_presigned_url(s3_url: str, expiration: int = 3600) -> str:
    """Generate presigned URL - convenience function"""
    s3_service = S3Service()
    return s3_service.generate_presigned_url(s3_url, expiration)