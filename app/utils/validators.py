"""
Validation utilities for Planogram Compliance application.
Handles image file validation and format checking.
"""
import logging
from typing import List, Tuple
from PIL import Image
from io import BytesIO
from app.config import config

# Setup logging
logger = logging.getLogger(__name__)

class ImageValidator:
    """Validator for image files and processing"""
    
    def __init__(self):
        self.supported_formats = config.SUPPORTED_IMAGE_FORMATS
        self.max_file_size = config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    def validate_single_image(self, image_file) -> Tuple[bool, str]:
        """
        Validate a single image file
        
        Args:
            image_file: Streamlit uploaded file object
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check file extension
            if not hasattr(image_file, 'name') or not image_file.name:
                return False, "Invalid file: No filename"
            
            file_ext = image_file.name.lower().split('.')[-1]
            if file_ext not in self.supported_formats:
                return False, f"Unsupported format '{file_ext}'. Supported: {', '.join(self.supported_formats)}"
            
            # Check file size
            if hasattr(image_file, 'size') and image_file.size > self.max_file_size:
                size_mb = round(image_file.size / (1024 * 1024), 2)
                return False, f"File too large: {size_mb}MB. Max size: {config.MAX_FILE_SIZE_MB}MB"
            
            # Try to validate actual image content
            try:
                image_file.seek(0)
                image_data = image_file.read()
                image_file.seek(0)  # Reset for later use
                
                # Verify it's a valid image
                with Image.open(BytesIO(image_data)) as img:
                    # Basic image validation
                    width, height = img.size
                    if width < 10 or height < 10:
                        return False, f"Image too small: {width}x{height}px"
                    
                    if width > 10000 or height > 10000:
                        return False, f"Image too large: {width}x{height}px. Max: 10000x10000px"
                
                logger.debug(f"✅ Valid image: {image_file.name} ({width}x{height})")
                return True, "Valid"
                
            except Exception as img_error:
                return False, f"Invalid image file: {str(img_error)}"
            
        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def validate_images(self, uploaded_images: List) -> Tuple[bool, str]:
        """
        Validate multiple uploaded images
        
        Args:
            uploaded_images: List of Streamlit uploaded file objects
            
        Returns:
            (is_valid, error_summary)
        """
        try:
            if not uploaded_images:
                return False, "No images uploaded"
            
            errors = []
            valid_count = 0
            
            for i, image_file in enumerate(uploaded_images, 1):
                is_valid, error_msg = self.validate_single_image(image_file)
                
                if is_valid:
                    valid_count += 1
                else:
                    errors.append(f"Image {i} ({image_file.name}): {error_msg}")
            
            # Summary results
            total_images = len(uploaded_images)
            
            if valid_count == total_images:
                logger.info(f"✅ All {total_images} images validated successfully")
                return True, f"All {total_images} images are valid"
            
            elif valid_count > 0:
                error_summary = f"{valid_count}/{total_images} images valid. Issues:\n" + "\n".join(errors)
                logger.warning(f"⚠️ Partial validation: {error_summary}")
                return False, error_summary
            
            else:
                error_summary = f"No valid images found. Issues:\n" + "\n".join(errors)
                logger.error(f"❌ {error_summary}")
                return False, error_summary
                
        except Exception as e:
            error_msg = f"Image validation failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def get_image_info(self, image_file) -> dict:
        """
        Get detailed information about an image file
        
        Args:
            image_file: Streamlit uploaded file object
            
        Returns:
            info: Dict with image details
        """
        try:
            image_file.seek(0)
            image_data = image_file.read()
            image_file.seek(0)  # Reset for later use
            
            with Image.open(BytesIO(image_data)) as img:
                info = {
                    'filename': image_file.name,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size_bytes': len(image_data),
                    'file_size_mb': round(len(image_data) / (1024 * 1024), 2)
                }
                
                return info
                
        except Exception as e:
            logger.error(f"Failed to get image info: {str(e)}")
            return {
                'filename': image_file.name if hasattr(image_file, 'name') else 'Unknown',
                'error': str(e)
            }
    
    def detect_image_format(self, image_bytes: bytes) -> str:
        """
        Detect image format from binary data
        
        Args:
            image_bytes: Image binary data
            
        Returns:
            format: Detected image format
        """
        try:
            if image_bytes.startswith(b'\xff\xd8\xff'):
                return 'jpeg'
            elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'png'
            elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
                return 'gif'
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
                return 'webp'
            else:
                return 'unknown'
                
        except Exception:
            return 'unknown'
    
    def validate_batch_size(self, uploaded_images: List) -> Tuple[bool, str]:
        """
        Validate if batch size is reasonable for processing
        
        Args:
            uploaded_images: List of uploaded images
            
        Returns:
            (is_acceptable, recommendation)
        """
        image_count = len(uploaded_images)
        
        if image_count == 0:
            return False, "No images to process"
        
        elif image_count <= 10:
            return True, f"Small batch: {image_count} images - optimal for processing"
        
        elif image_count <= 50:
            return True, f"Medium batch: {image_count} images - good for processing"
        
        elif image_count <= 200:
            return True, f"Large batch: {image_count} images - may take longer to process"
        
        else:
            return False, f"Very large batch: {image_count} images - consider splitting into smaller batches for better performance"


# Convenience functions for backward compatibility
def validate_images(uploaded_images: List) -> Tuple[bool, str, List]:
    """
    Validate uploaded images - convenience function
    
    Returns:
        (is_valid, error_message, validated_images)
    """
    validator = ImageValidator()
    is_valid, error_msg = validator.validate_images(uploaded_images)
    
    # Return validated images (all images if validation passed)
    validated_images = uploaded_images if is_valid else []
    
    return is_valid, error_msg, validated_images

def detect_image_format(image_bytes: bytes) -> str:
    """Detect image format - convenience function"""
    validator = ImageValidator()
    return validator.detect_image_format(image_bytes)