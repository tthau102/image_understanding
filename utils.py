import pandas as pd
import logging
from typing import List, Dict, Tuple
import os
from config import SUPPORTED_IMAGE_FORMATS, MAX_FILE_SIZE_MB, CSV_ENCODING

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_csv_file(csv_file) -> Tuple[bool, str, pd.DataFrame]:
    """
    Validate CSV file and return DataFrame
    
    Returns:
        (is_valid, error_message, dataframe)
    """
    try:
        # Check file size
        if csv_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return False, f"CSV file too large. Max size: {MAX_FILE_SIZE_MB}MB", None
        
        # Read CSV
        csv_file.seek(0)  # Reset file pointer
        df = pd.read_csv(csv_file, encoding=CSV_ENCODING)
        
        # Check required columns
        required_columns = ['image_name', 'value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}", None
        
        # Check for empty DataFrame
        if df.empty:
            return False, "CSV file is empty", None
        
        # Log CSV info
        logger.info(f"CSV validated successfully: {len(df)} records found")
        
        return True, "Valid", df
        
    except Exception as e:
        logger.error(f"CSV validation error: {str(e)}")
        return False, f"CSV validation error: {str(e)}", None

def validate_images(uploaded_images) -> Tuple[bool, str, List]:
    """
    Validate uploaded images
    
    Returns:
        (is_valid, error_message, validated_images)
    """
    try:
        if not uploaded_images:
            return False, "No images uploaded", []
        
        validated_images = []
        errors = []
        
        for img in uploaded_images:
            # Check file extension
            file_ext = img.name.lower().split('.')[-1]
            if file_ext not in SUPPORTED_IMAGE_FORMATS:
                errors.append(f"{img.name}: Unsupported format. Use: {SUPPORTED_IMAGE_FORMATS}")
                continue
            
            # Check file size
            if img.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                errors.append(f"{img.name}: File too large. Max: {MAX_FILE_SIZE_MB}MB")
                continue
            
            validated_images.append(img)
        
        if errors:
            error_msg = "Image validation errors:\n" + "\n".join(errors)
            logger.warning(error_msg)
            return len(validated_images) > 0, error_msg, validated_images
        
        logger.info(f"Images validated successfully: {len(validated_images)} images")
        return True, "Valid", validated_images
        
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        return False, f"Image validation error: {str(e)}", []

def match_csv_with_images(df: pd.DataFrame, uploaded_images: List) -> Tuple[List[Dict], List[str]]:
    """
    Match CSV records with uploaded images
    
    Returns:
        (matched_records, missing_items_log)
    """
    matched_records = []
    missing_items = []
    
    # Create image lookup dictionary
    image_lookup = {}
    for img in uploaded_images:
        # Extract image name without extension
        img_name = img.name.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
        image_lookup[img_name] = img
    
    logger.info(f"Processing CSV records: {len(df)} total")
    logger.info(f"Available images: {len(image_lookup)} total")
    
    # Process each CSV record
    for index, row in df.iterrows():
        image_name = str(row['image_name']).strip()
        description = str(row['value']).strip()
        
        # Check if corresponding image exists
        if image_name in image_lookup:
            matched_records.append({
                'image_name': image_name,
                'description': description,
                'image_file': image_lookup[image_name]
            })
            logger.info(f"✅ Matched: {image_name}")
        else:
            missing_msg = f"❌ Missing image for CSV record: {image_name}"
            missing_items.append(missing_msg)
            logger.warning(missing_msg)
    
    # Check for images without CSV records
    for img_name in image_lookup.keys():
        if not any(record['image_name'] == img_name for record in matched_records):
            missing_msg = f"❌ Missing CSV record for image: {img_name}.jpg"
            missing_items.append(missing_msg)
            logger.warning(missing_msg)
    
    logger.info(f"✅ Successfully matched: {len(matched_records)} records")
    logger.info(f"❌ Missing items: {len(missing_items)}")
    
    return matched_records, missing_items

def detect_image_format(image_bytes) -> str:
    """Detect image format from binary data"""
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    else:
        return 'jpeg'  # Default fallback