import boto3
import logging
from datetime import datetime
from typing import List, Dict
from decimal import Decimal
import json

from config import (S3_BUCKET_NAME, S3_REGION,
                    DYNAMODB_TABLE_NAME, DYNAMODB_REGION)

# Try to import Postgres settings if they exist
try:
    from config import DB_CONFIG, DB_RESULT
except Exception:
    DB_CONFIG, DB_RESULT = None, None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=S3_REGION)
dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)

# DynamoDB helper functions
def convert_decimal_to_native(obj):
    """Convert DynamoDB Decimal types to native Python types for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimal_to_native(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_native(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise to float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj

def convert_native_to_decimal(obj):
    """Convert native Python numbers to Decimal for DynamoDB"""
    if isinstance(obj, list):
        return [convert_native_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_native_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, int):
        return Decimal(obj)
    else:
        return obj

# DynamoDB connection and operations
def get_dynamodb_table():
    """Get DynamoDB table resource"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        logger.info(f"✅ Connected to DynamoDB table: {DYNAMODB_TABLE_NAME}")
        return table
    except Exception as e:
        logger.error(f"❌ DynamoDB connection failed: {str(e)}")
        raise

def get_pending_review_items_dynamodb() -> List[Dict]:
    """
    Get all pending review items from DynamoDB table

    Returns:
        List of dictionaries containing pending review data
    """
    try:
        table = get_dynamodb_table()

        # Scan the entire table (for small datasets)
        # For larger datasets, consider using pagination
        response = table.scan()
        
        pending_items = []
        for item in response['Items']:
            # Convert DynamoDB item to standard format
            processed_item = {
                'id': item.get('id', ''),
                'image_name': item.get('image_name', ''),
                's3_url': item.get('s3_url', ''),
                'product_count': convert_decimal_to_native(item.get('product_count', {})),
                'compliance_assessment': bool(item.get('compliance_assessment', False)),
                'review_comment': item.get('review_comment', ''),
                'timestamp': item.get('timestamp', ''),
                'need_review': bool(item.get('need_review', False))
            }
            pending_items.append(processed_item)

        # Sort by timestamp descending (newest first)
        pending_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"🔍 Found {len(pending_items)} items in DynamoDB")
        return pending_items

    except Exception as e:
        logger.error(f"❌ Failed to get items from DynamoDB: {str(e)}")
        return []

def get_item_by_id_dynamodb(item_id: str) -> Dict:
    """
    Get a specific item by ID from DynamoDB

    Args:
        item_id: The ID of the item to retrieve

    Returns:
        Dictionary containing the item data, or empty dict if not found
    """
    try:
        table = get_dynamodb_table()
        
        response = table.get_item(
            Key={'id': item_id}
        )
        
        if 'Item' in response:
            item = response['Item']
            processed_item = {
                'id': item.get('id', ''),
                'image_name': item.get('image_name', ''),
                's3_url': item.get('s3_url', ''),
                'product_count': convert_decimal_to_native(item.get('product_count', {})),
                'compliance_assessment': bool(item.get('compliance_assessment', False)),
                'review_comment': item.get('review_comment', ''),
                'timestamp': item.get('timestamp', ''),
                'need_review': bool(item.get('need_review', False))
            }
            logger.info(f"✅ Retrieved item {item_id} from DynamoDB")
            return processed_item
        else:
            logger.info(f"📝 Item {item_id} not found in DynamoDB")
            return {}

    except Exception as e:
        logger.error(f"❌ Failed to get item {item_id} from DynamoDB: {str(e)}")
        return {}

def update_item_dynamodb(item_id: str, updates: Dict) -> bool:
    """
    Update an item in DynamoDB

    Args:
        item_id: The ID of the item to update
        updates: Dictionary of fields to update

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table = get_dynamodb_table()
        
        # Build update expression
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        update_parts = []
        for key, value in updates.items():
            # Handle reserved keywords by using expression attribute names
            attr_name = f"#{key}"
            attr_value = f":{key}"
            
            update_parts.append(f"{attr_name} = {attr_value}")
            expression_attribute_names[attr_name] = key
            
            # Convert to Decimal if needed
            expression_attribute_values[attr_value] = convert_native_to_decimal(value)
        
        update_expression += ", ".join(update_parts)
        
        response = table.update_item(
            Key={'id': item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
        
        logger.info(f"✅ Updated item {item_id} in DynamoDB")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update item {item_id} in DynamoDB: {str(e)}")
        return False

def insert_item_dynamodb(item_data: Dict) -> bool:
    """
    Insert a new item into DynamoDB

    Args:
        item_data: Dictionary containing the item data

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table = get_dynamodb_table()
        
        # Convert data to DynamoDB format
        dynamodb_item = convert_native_to_decimal(item_data)
        
        # Add timestamp if not provided
        if 'timestamp' not in dynamodb_item:
            dynamodb_item['timestamp'] = datetime.now().isoformat()
        
        table.put_item(Item=dynamodb_item)
        
        logger.info(f"✅ Inserted new item {item_data.get('id', 'unknown')} into DynamoDB")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to insert item into DynamoDB: {str(e)}")
        return False

def delete_item_dynamodb(item_id: str) -> bool:
    """
    Delete an item from DynamoDB

    Args:
        item_id: The ID of the item to delete

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table = get_dynamodb_table()
        
        table.delete_item(
            Key={'id': item_id}
        )
        
        logger.info(f"✅ Deleted item {item_id} from DynamoDB")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to delete item {item_id} from DynamoDB: {str(e)}")
        return False

def get_items_by_compliance_dynamodb(compliance_status: bool) -> List[Dict]:
    """
    Get items filtered by compliance status from DynamoDB

    Args:
        compliance_status: True for compliant items, False for non-compliant

    Returns:
        List of dictionaries containing filtered items
    """
    try:
        table = get_dynamodb_table()
        
        # Use scan with filter expression
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('compliance_assessment').eq(compliance_status)
        )
        
        pending_items = []
        for item in response['Items']:
            processed_item = {
                'id': item.get('id', ''),
                'image_name': item.get('image_name', ''),
                's3_url': item.get('s3_url', ''),
                'product_count': convert_decimal_to_native(item.get('product_count', {})),
                'compliance_assessment': bool(item.get('compliance_assessment', False)),
                'review_comment': item.get('review_comment', ''),
                'timestamp': item.get('timestamp', ''),
                'need_review': bool(item.get('need_review', False))
            }
            pending_items.append(processed_item)

        # Sort by timestamp descending
        pending_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"🔍 Found {len(pending_items)} items with compliance_assessment={compliance_status}")
        return pending_items

    except Exception as e:
        logger.error(f"❌ Failed to filter items by compliance status: {str(e)}")
        return []

def get_items_needing_review_dynamodb() -> List[Dict]:
    """
    Get items that need review from DynamoDB

    Returns:
        List of dictionaries containing items that need review
    """
    try:
        table = get_dynamodb_table()
        
        # Use scan with filter expression for need_review = true
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('need_review').eq(True)
        )
        
        pending_items = []
        for item in response['Items']:
            processed_item = {
                'id': item.get('id', ''),
                'image_name': item.get('image_name', ''),
                's3_url': item.get('s3_url', ''),
                'product_count': convert_decimal_to_native(item.get('product_count', {})),
                'compliance_assessment': bool(item.get('compliance_assessment', False)),
                'review_comment': item.get('review_comment', ''),
                'timestamp': item.get('timestamp', ''),
                'need_review': bool(item.get('need_review', False))
            }
            pending_items.append(processed_item)

        # Sort by timestamp descending
        pending_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"🔍 Found {len(pending_items)} items needing review")
        return pending_items

    except Exception as e:
        logger.error(f"❌ Failed to get items needing review: {str(e)}")
        return []

# Keep existing PostgreSQL functions for backward compatibility
import psycopg2

def get_db_connection():
    """Get PostgreSQL database connection (LEGACY - kept for backward compatibility)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise

def get_pending_review_items(conn) -> List[Dict]:
    """
    Get all pending review items from PostgreSQL results table (LEGACY)

    Args:
        conn: Database connection

    Returns:
        List of dictionaries containing pending review data
    """
    try:
        cursor = conn.cursor()

        query = f"""
            SELECT id, image_name, s3_url, product_count, compliance_assessment, review_comment, timestamp
            FROM {DB_RESULT}
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

# S3 functions remain unchanged
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
        # Extract bucket and key from S3 URL
        # Format: https://bucket-name.s3.region.amazonaws.com/key
        if not s3_url or not s3_url.startswith('https://'):
            return s3_url

        # Parse S3 URL to extract bucket and key
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

def upload_image_to_s3(image_file, bucket_name: str, folder_prefix: str = "uploaded_images") -> tuple:
    """
    Upload single image to S3 bucket (private)
    
    Args:
        image_file: Streamlit uploaded file
        bucket_name: S3 bucket name
        folder_prefix: S3 folder prefix
        
    Returns:
        tuple: (s3_url, s3_key)
    """
    try:
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image_file.name}"
        s3_key = f"{folder_prefix}/{filename}"
        
        # Reset file pointer
        image_file.seek(0)
        
        # Upload to S3 with proper content type
        content_type = "image/jpeg" if image_file.name.lower().endswith(('.jpg', '.jpeg')) else "image/png"
        
        s3_client.upload_fileobj(
            image_file,
            bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256'
            }
        )
        
        s3_url = f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"✅ Uploaded to S3: {filename}")
        
        return s3_url, s3_key
        
    except Exception as e:
        logger.error(f"❌ S3 upload failed for {image_file.name}: {str(e)}")
        raise