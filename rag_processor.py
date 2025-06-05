import logging
from typing import List, Dict, Tuple
import time

from utils import validate_csv_file, validate_images, match_csv_with_images
from data_ops import create_s3_folder, upload_csv_to_s3, process_image_record

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGProcessor:
    """Main processor for RAG data ingestion workflow"""
    
    def __init__(self):
        self.processing_results = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0,
            'errors': [],
            'success_items': [],
            's3_folder': '',
            'csv_s3_url': ''
        }
    
    def validate_inputs(self, csv_file, uploaded_images) -> Tuple[bool, str]:
        """
        Validate CSV and images inputs
        
        Returns:
            (is_valid, error_message)
        """
        logger.info("🔍 Starting input validation...")
        
        # Validate CSV
        csv_valid, csv_error, self.df = validate_csv_file(csv_file)
        if not csv_valid:
            return False, f"CSV Error: {csv_error}"
        
        # Validate Images
        images_valid, images_error, self.validated_images = validate_images(uploaded_images)
        if not images_valid:
            return False, f"Images Error: {images_error}"
        
        logger.info("✅ Input validation completed successfully")
        return True, "Validation passed"
    
    def match_data(self) -> Tuple[bool, str]:
        """
        Match CSV records with images
        
        Returns:
            (has_matches, status_message)
        """
        logger.info("🔗 Starting CSV-Image matching...")
        
        self.matched_records, self.missing_items = match_csv_with_images(
            self.df, self.validated_images
        )
        
        if not self.matched_records:
            return False, "No matching records found between CSV and images"
        
        # Store missing items in results
        self.processing_results['errors'].extend(self.missing_items)
        
        logger.info(f"✅ Matching completed: {len(self.matched_records)} records ready for processing")
        return True, f"Found {len(self.matched_records)} matching records"
    
    def setup_s3_storage(self, csv_file) -> Tuple[bool, str]:
        """
        Create S3 folder and upload CSV
        
        Returns:
            (success, status_message)
        """
        try:
            logger.info("☁️ Setting up S3 storage...")
            
            # Create timestamped S3 folder
            self.s3_folder = create_s3_folder()
            self.processing_results['s3_folder'] = self.s3_folder
            
            # Upload CSV to S3
            csv_s3_url = upload_csv_to_s3(csv_file, self.s3_folder)
            self.processing_results['csv_s3_url'] = csv_s3_url
            
            logger.info(f"✅ S3 setup completed: {self.s3_folder}")
            return True, f"S3 folder created: {self.s3_folder}"
            
        except Exception as e:
            error_msg = f"S3 setup failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def process_records(self) -> Tuple[bool, str]:
        """
        Process all matched records: embeddings + S3 + DB
        
        Returns:
            (success, status_message)
        """
        start_time = time.time()
        logger.info(f"🚀 Starting processing of {len(self.matched_records)} records...")
        
        self.processing_results['total_records'] = len(self.matched_records)
        
        for i, record in enumerate(self.matched_records, 1):
            logger.info(f"Processing record {i}/{len(self.matched_records)}: {record['image_name']}")
            
            try:
                success, error_msg = process_image_record(record, self.s3_folder)
                
                if success:
                    self.processing_results['successful'] += 1
                    self.processing_results['success_items'].append(record['image_name'])
                    logger.info(f"✅ [{i}/{len(self.matched_records)}] Success: {record['image_name']}")
                else:
                    self.processing_results['failed'] += 1
                    self.processing_results['errors'].append(f"{record['image_name']}: {error_msg}")
                    logger.error(f"❌ [{i}/{len(self.matched_records)}] Failed: {record['image_name']} - {error_msg}")
                    
            except Exception as e:
                self.processing_results['failed'] += 1
                error_msg = f"{record['image_name']}: Unexpected error - {str(e)}"
                self.processing_results['errors'].append(error_msg)
                logger.error(f"❌ [{i}/{len(self.matched_records)}] Exception: {error_msg}")
        
        # Calculate processing time
        self.processing_results['processing_time'] = round(time.time() - start_time, 2)
        
        # Determine overall success
        if self.processing_results['successful'] > 0:
            success_msg = f"Processing completed: {self.processing_results['successful']}/{self.processing_results['total_records']} successful"
            logger.info(f"✅ {success_msg}")
            return True, success_msg
        else:
            failure_msg = "Processing failed: No records were processed successfully"
            logger.error(f"❌ {failure_msg}")
            return False, failure_msg
    
    def run_full_workflow(self, csv_file, uploaded_images) -> Dict:
        """
        Run complete RAG data ingestion workflow
        
        Returns:
            processing_results: Dict with complete results
        """
        logger.info("🎯 Starting RAG Data Ingestion Workflow...")
        
        try:
            # Step 1: Validate inputs
            valid, error = self.validate_inputs(csv_file, uploaded_images)
            if not valid:
                self.processing_results['errors'].append(f"Validation Error: {error}")
                return self.processing_results
            
            # Step 2: Match CSV with images
            has_matches, match_msg = self.match_data()
            if not has_matches:
                self.processing_results['errors'].append(f"Matching Error: {match_msg}")
                return self.processing_results
            
            # Step 3: Setup S3 storage
            s3_success, s3_msg = self.setup_s3_storage(csv_file)
            if not s3_success:
                self.processing_results['errors'].append(f"S3 Error: {s3_msg}")
                return self.processing_results
            
            # Step 4: Process all records
            process_success, process_msg = self.process_records()
            
            # Final summary
            logger.info("🏁 RAG Data Ingestion Workflow Completed!")
            logger.info(f"📊 Results Summary:")
            logger.info(f"   Total Records: {self.processing_results['total_records']}")
            logger.info(f"   Successful: {self.processing_results['successful']}")
            logger.info(f"   Failed: {self.processing_results['failed']}")
            logger.info(f"   Processing Time: {self.processing_results['processing_time']}s")
            logger.info(f"   S3 Folder: {self.processing_results['s3_folder']}")
            
            return self.processing_results
            
        except Exception as e:
            error_msg = f"Workflow failed with unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.processing_results['errors'].append(error_msg)
            return self.processing_results