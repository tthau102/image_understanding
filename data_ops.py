import boto3
import psycopg2
import logging
from typing import List, Dict
from config import S3_REGION, DB_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize AWS S3 client
s3_client = boto3.client('s3', region_name=S3_REGION)

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise

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

        query = """
            SELECT id, image_name, s3_url, product_count, compliance_assessment, review_comment, timestamp
            FROM results
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

def generate_presigned_url(s3_url: str, expiration: int = 3600) -> str:
    """
    Generate presigned URL for S3 object

    Args:
        s3_url: Original S3 URL
        expiration: URL expiration time in seconds (default: 1 hour)

    Returns:
        presigned_url: Presigned URL for accessing the S3 object
    """
    try:
        # Validate input
        if not s3_url or not s3_url.startswith('https://'):
            logger.warning(f"Invalid S3 URL: {s3_url}")
            return s3_url

        # Parse S3 URL to extract bucket and key
        # Format: https://bucket-name.s3.region.amazonaws.com/key
        url_parts = s3_url.replace('https://', '').split('/')
        bucket_part = url_parts[0]  # bucket-name.s3.region.amazonaws.com
        key = '/'.join(url_parts[1:])  # path/to/object

        # Extract bucket name (everything before .s3.)
        bucket_name = bucket_part.split('.s3.')[0]

        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
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