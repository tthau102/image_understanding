"""
Image processing and storage service for Planogram Compliance application.
Handles image uploads, validation, and Label Studio integration workflow.
"""
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from app.config import config
from app.services.data_ops import S3Service
from app.services.labelstudio_service import LabelStudioService
from app.utils.validators import ImageValidator

# Setup logging
logger = logging.getLogger(__name__)

class ImageProcessor:
    """Main processor for image upload and Label Studio integration workflow"""
    
    def __init__(self):
        self.s3_service = S3Service()
        self.ls_service = LabelStudioService()
        self.validator = ImageValidator()
        
        self.processing_results = {
            'total_images': 0,
            'upload_successful': 0,
            'upload_failed': 0,
            'import_successful': False,
            'task_count': 0,
            'processing_time': 0,
            'errors': [],
            's3_folder': '',
            'storage_id': None
        }
    
    def validate_inputs(self, uploaded_images: List, project_id: int) -> Tuple[bool, str]:
        """
        Validate images and project selection
        
        Args:
            uploaded_images: List of Streamlit uploaded file objects
            project_id: Selected Label Studio project ID
            
        Returns:
            (is_valid, error_message)
        """
        logger.info("🔍 Starting input validation...")
        
        # Validate project selection
        if not project_id:
            return False, "Please select a Label Studio project"
        
        # Validate images
        if not uploaded_images:
            return False, "Please upload at least one image"
        
        # Validate each image
        images_valid, images_error = self.validator.validate_images(uploaded_images)
        if not images_valid:
            return False, f"Image validation failed: {images_error}"
        
        logger.info(f"✅ Input validation completed: {len(uploaded_images)} images, project {project_id}")
        return True, "Validation passed"
    
    def upload_images_to_s3(self, uploaded_images: List, project_id: int) -> Tuple[bool, str]:
        """
        Upload images to S3 in project-specific folder
        
        Args:
            uploaded_images: List of validated image files
            project_id: Label Studio project ID
            
        Returns:
            (success, status_message)
        """
        try:
            logger.info(f"☁️ Starting S3 upload for {len(uploaded_images)} images...")
            
            # Upload images in batch
            upload_results = self.s3_service.upload_images_batch(uploaded_images, project_id)
            
            # Update processing results
            self.processing_results.update({
                'total_images': upload_results['total_images'],
                'upload_successful': upload_results['successful'],
                'upload_failed': upload_results['failed'],
                's3_folder': upload_results['s3_folder'],
                'processing_time': upload_results['processing_time']
            })
            
            # Add any upload errors
            self.processing_results['errors'].extend(upload_results['errors'])
            
            if upload_results['successful'] > 0:
                success_msg = f"Uploaded {upload_results['successful']}/{upload_results['total_images']} images to S3"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                failure_msg = "No images were uploaded successfully"
                logger.error(f"❌ {failure_msg}")
                return False, failure_msg
                
        except Exception as e:
            error_msg = f"S3 upload failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.processing_results['errors'].append(error_msg)
            return False, error_msg
    
    def sync_with_labelstudio(self, project_id: int) -> Tuple[bool, str]:
        """
        Create S3 storage connection and sync with Label Studio
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            (success, status_message)
        """
        try:
            logger.info(f"🔄 Starting Label Studio integration for project {project_id}...")
            
            # Import images to Label Studio
            import_result = self.ls_service.import_images_to_project(
                project_id, 
                self.processing_results['s3_folder']
            )
            
            if import_result['success']:
                # Update processing results
                self.processing_results.update({
                    'import_successful': True,
                    'task_count': import_result['task_count'],
                    'storage_id': import_result['storage_id']
                })
                
                success_msg = f"Successfully imported {import_result['task_count']} tasks to Label Studio"
                logger.info(f"✅ {success_msg}")
                return True, success_msg
            else:
                error_msg = f"Label Studio import failed: {import_result['error']}"
                logger.error(f"❌ {error_msg}")
                self.processing_results['errors'].append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Label Studio sync failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.processing_results['errors'].append(error_msg)
            return False, error_msg
    
    def run_full_workflow(self, uploaded_images: List, project_id: int) -> Dict:
        """
        Run complete image processing and Label Studio integration workflow
        
        Args:
            uploaded_images: List of Streamlit uploaded file objects
            project_id: Selected Label Studio project ID
            
        Returns:
            processing_results: Dict with complete workflow results
        """
        start_time = datetime.now()
        logger.info("🎯 Starting Image Processing Workflow...")
        
        try:
            # Step 1: Validate inputs
            valid, error = self.validate_inputs(uploaded_images, project_id)
            if not valid:
                self.processing_results['errors'].append(f"Validation Error: {error}")
                return self.processing_results
            
            # Step 2: Upload images to S3
            upload_success, upload_msg = self.upload_images_to_s3(uploaded_images, project_id)
            if not upload_success:
                self.processing_results['errors'].append(f"Upload Error: {upload_msg}")
                return self.processing_results
            
            # Step 3: Sync with Label Studio
            sync_success, sync_msg = self.sync_with_labelstudio(project_id)
            if not sync_success:
                self.processing_results['errors'].append(f"Sync Error: {sync_msg}")
                # Note: S3 upload was successful, so this is partial success
            
            # Calculate total processing time
            total_time = (datetime.now() - start_time).total_seconds()
            self.processing_results['processing_time'] = round(total_time, 2)
            
            # Final summary
            if self.processing_results['import_successful']:
                logger.info("🎉 Complete workflow finished successfully!")
            else:
                logger.warning("⚠️ Workflow completed with issues")
            
            logger.info(f"📊 Final Results:")
            logger.info(f"   Images Uploaded: {self.processing_results['upload_successful']}/{self.processing_results['total_images']}")
            logger.info(f"   Label Studio Tasks: {self.processing_results['task_count']}")
            logger.info(f"   Processing Time: {self.processing_results['processing_time']}s")
            logger.info(f"   S3 Folder: {self.processing_results['s3_folder']}")
            
            return self.processing_results
            
        except Exception as e:
            error_msg = f"Workflow failed with unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.processing_results['errors'].append(error_msg)
            return self.processing_results
    
    def get_workflow_summary(self) -> str:
        """
        Get human-readable summary of workflow results
        
        Returns:
            summary: Formatted summary string
        """
        results = self.processing_results
        
        if results['import_successful']:
            return f"✅ Success: {results['upload_successful']} images uploaded, {results['task_count']} tasks created in Label Studio"
        elif results['upload_successful'] > 0:
            return f"⚠️ Partial: {results['upload_successful']} images uploaded to S3, but Label Studio sync failed"
        else:
            return f"❌ Failed: No images processed successfully"