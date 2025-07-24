"""
Label Studio integration service for Planogram Compliance application.
Handles API communication, project management, and storage sync.
"""
import requests
import logging
from typing import List, Dict, Optional
from app.config import config

# Setup logging
logger = logging.getLogger(__name__)

class LabelStudioService:
    """Service for Label Studio API operations"""
    
    def __init__(self):
        self.base_url = config.LABEL_STUDIO_URL.rstrip('/')
        self.api_token = config.LABEL_STUDIO_API_TOKEN
        self.headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def get_projects(self) -> Dict:
        """
        Get all Label Studio projects
        
        Returns:
            result: Dict with success status and projects list
        """
        try:
            url = f"{self.base_url}/api/projects"
            logger.info(f"🔍 Fetching projects from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get('results', data) if isinstance(data, dict) else data
                
                logger.info(f"✅ Found {len(projects)} Label Studio projects")
                return {
                    'success': True,
                    'projects': projects,
                    'count': len(projects)
                }
            
            elif response.status_code == 401:
                error_msg = "Authentication failed. Please check LABEL_STUDIO_API_TOKEN"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': 401
                }
            
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout. Please check Label Studio server"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
            
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error. Please check LABEL_STUDIO_URL"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def get_project_details(self, project_id: int) -> Dict:
        """
        Get detailed information about a specific project
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            result: Dict with project details
        """
        try:
            url = f"{self.base_url}/api/projects/{project_id}"
            logger.info(f"🔍 Fetching project details: {project_id}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                project_data = response.json()
                logger.info(f"✅ Got project details: {project_data.get('title', 'Unknown')}")
                return {
                    'success': True,
                    'project': project_data
                }
            else:
                error_msg = f"Failed to get project {project_id}: {response.status_code}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Error getting project details: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def create_s3_storage(self, project_id: int, s3_folder: str) -> Dict:
        """
        Create or update S3 storage connection for a Label Studio project
        
        Args:
            project_id: Label Studio project ID
            s3_folder: S3 folder path containing images
            
        Returns:
            result: Dict with success status and storage info
        """
        try:
            url = f"{self.base_url}/api/storages/s3"
            logger.info(f"🔧 Creating S3 storage for project {project_id}")
            
            # Prepare storage configuration
            storage_config = {
                "title": f"S3 Storage - Project {project_id}",
                "bucket": config.S3_BUCKET_NAME,
                "prefix": s3_folder,
                "region_name": config.S3_REGION,
                "project": project_id,
                "use_blob_urls": True,  # Treat objects as files, generate URLs
                "regex_filter": ".*\\.(jpg|jpeg|png)$",  # Only import image files
                "presign": True,
                "presign_ttl": 3600
            }
            
            # Add AWS credentials if available
            if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
                storage_config.update({
                    "aws_access_key_id": config.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": config.AWS_SECRET_ACCESS_KEY
                })
            
            response = requests.post(
                url, 
                json=storage_config, 
                headers=self.headers, 
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                storage_data = response.json()
                storage_id = storage_data.get('id')
                
                logger.info(f"✅ Created S3 storage {storage_id} for project {project_id}")
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'storage_data': storage_data
                }
            else:
                error_msg = f"Failed to create S3 storage: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error creating S3 storage: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def sync_s3_storage(self, storage_id: int) -> Dict:
        """
        Sync S3 storage to import tasks into Label Studio
        
        Args:
            storage_id: Label Studio storage connection ID
            
        Returns:
            result: Dict with sync status and task count
        """
        try:
            url = f"{self.base_url}/api/storages/s3/{storage_id}/sync"
            logger.info(f"🔄 Syncing S3 storage {storage_id}")
            
            response = requests.post(url, headers=self.headers, timeout=60)
            
            if response.status_code in [200, 201]:
                sync_data = response.json()
                task_count = sync_data.get('task_count', 0)
                
                logger.info(f"✅ Synced S3 storage: {task_count} tasks imported")
                return {
                    'success': True,
                    'task_count': task_count,
                    'sync_data': sync_data
                }
            else:
                error_msg = f"Failed to sync S3 storage: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"Error syncing S3 storage: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def import_images_to_project(self, project_id: int, s3_folder: str) -> Dict:
        """
        Complete workflow: Create S3 storage + Sync for a project
        
        Args:
            project_id: Label Studio project ID
            s3_folder: S3 folder path containing uploaded images
            
        Returns:
            result: Dict with complete import status
        """
        try:
            logger.info(f"🚀 Starting image import for project {project_id}")
            
            # Step 1: Create S3 storage connection
            storage_result = self.create_s3_storage(project_id, s3_folder)
            if not storage_result['success']:
                return {
                    'success': False,
                    'error': f"Storage creation failed: {storage_result['error']}",
                    'step': 'create_storage'
                }
            
            storage_id = storage_result['storage_id']
            
            # Step 2: Sync storage to import tasks
            sync_result = self.sync_s3_storage(storage_id)
            if not sync_result['success']:
                return {
                    'success': False,
                    'error': f"Storage sync failed: {sync_result['error']}",
                    'step': 'sync_storage',
                    'storage_id': storage_id
                }
            
            task_count = sync_result['task_count']
            
            logger.info(f"🎉 Successfully imported {task_count} images to project {project_id}")
            return {
                'success': True,
                'storage_id': storage_id,
                'task_count': task_count,
                'message': f"Successfully imported {task_count} tasks to Label Studio"
            }
            
        except Exception as e:
            error_msg = f"Import workflow failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def get_storage_connections(self, project_id: int) -> Dict:
        """
        Get all S3 storage connections for a project
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            result: Dict with storage connections list
        """
        try:
            url = f"{self.base_url}/api/storages/s3"
            params = {'project': project_id}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                storage_list = response.json()
                return {
                    'success': True,
                    'storages': storage_list,
                    'count': len(storage_list)
                }
            else:
                error_msg = f"Failed to get storage connections: {response.status_code}"
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error getting storage connections: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def validate_connection(self) -> Dict:
        """
        Test Label Studio API connection and authentication
        
        Returns:
            result: Dict with connection status
        """
        try:
            logger.info("🔍 Validating Label Studio connection...")
            
            # Simple API call to validate connection
            result = self.get_projects()
            
            if result['success']:
                logger.info("✅ Label Studio connection validated successfully")
                return {
                    'success': True,
                    'message': "Connection successful",
                    'project_count': result['count']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            error_msg = f"Connection validation failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}