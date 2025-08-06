import streamlit as st
import logging
import json
import pandas as pd
from data_ops import get_db_connection, get_pending_review_items, generate_presigned_url
import requests
import boto3
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Planogram Compliance",
    page_icon="📊"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        padding: 20px 0;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .result-success {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .result-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
    }
    .result-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 20px 0;
    }
    .stat-box {
        text-align: center;
        padding: 15px;
        background-color: #e9ecef;
        border-radius: 8px;
        min-width: 120px;
    }
    .stat-number {
        font-size: 2em;
        font-weight: bold;
        color: #2E86AB;
    }
    .review-item {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    .review-image {
        text-align: center;
        padding: 10px;
    }
    .review-result {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ced4da;
    }
</style>
""", unsafe_allow_html=True)

# Configuration for Image Upload & Label Studio Sync
try:
    from config import (
        LABEL_STUDIO_API_TOKEN, 
        S3_BUCKET_NAME, 
        S3_REGION,
        LABEL_STUDIO_PROJECT_ID,
        LABEL_STUDIO_BASE_URL
    )
except ImportError:
    # Fallback to sample config
    from config_sample import (
        LABEL_STUDIO_API_TOKEN,
        S3_BUCKET_NAME, 
        S3_REGION,
        LABEL_STUDIO_PROJECT_ID,
        LABEL_STUDIO_BASE_URL
    )

# Initialize S3 client
s3_client = boto3.client('s3', region_name=S3_REGION)

def get_s3_folders(bucket_name, prefix):
    """
    Get list of folders in S3 bucket with given prefix

    Args:
        bucket_name: S3 bucket name
        prefix: Folder prefix to search

    Returns:
        list: List of folder names
    """
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            Delimiter='/'
        )

        folders = []
        if 'CommonPrefixes' in response:
            for prefix_info in response['CommonPrefixes']:
                folder_path = prefix_info['Prefix']
                # Extract folder name (remove prefix and trailing slash)
                folder_name = folder_path.replace(prefix, '').rstrip('/')
                if folder_name:  # Only add non-empty folder names
                    folders.append(folder_name)

        logger.info(f"✅ Found {len(folders)} folders in {bucket_name}/{prefix}")
        return folders

    except Exception as e:
        logger.error(f"❌ Failed to get S3 folders: {str(e)}")
        return []



def upload_image_to_s3(image_file, bucket_name, folder_prefix="uploaded_images"):
    """
    Upload single image to S3 bucket (private)
    
    Args:
        image_file: Streamlit uploaded file
        bucket_name: S3 bucket name
        folder_prefix: S3 folder prefix
        
    Returns:
        s3_url: S3 URL of uploaded image (private)
        s3_key: S3 key of the uploaded file
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

def trigger_labelstudio_storage_sync(project_id, api_token, base_url):
    """
    Trigger Label Studio Source Cloud Storage sync for specific project to detect new S3 files
    """
    try:
        headers = {"Authorization": f"Token {api_token}"}

        # Get Source Cloud Storage configurations for the specific project
        source_storage_url = f"{base_url}/api/storages/s3"
        response = requests.get(source_storage_url, headers=headers, params={"project": project_id})

        if response.status_code != 200:
            return False, {"details": f"Failed to get source storage configs: {response.status_code}"}

        storages = response.json()
        if not storages:
            return False, {"details": f"No Source Cloud Storage configured for project {project_id}"}

        # Find the source storage for this project (usually the first one or filter by project)
        project_storage = None
        for storage in storages:
            if storage.get('project') == int(project_id):
                project_storage = storage
                break

        if not project_storage:
            # If no project-specific storage found, use the first available
            project_storage = storages[0]

        storage_id = project_storage['id']
        storage_title = project_storage.get('title', 'Unknown')

        # Trigger sync for the Source Cloud Storage
        sync_trigger_url = f"{source_storage_url}/{storage_id}/sync"

        logger.info(f"🔄 Triggering sync for Source Storage: {storage_title} (ID: {storage_id})")
        sync_response = requests.post(sync_trigger_url, headers=headers)

        if sync_response.status_code in [200, 201]:
            sync_data = sync_response.json() if sync_response.content else {}
            logger.info(f"✅ Source Cloud Storage sync triggered successfully for project {project_id}")
            return True, {
                "status": "success",
                "storage_id": storage_id,
                "storage_title": storage_title,
                "sync_data": sync_data
            }
        else:
            error_msg = f"Sync failed with status {sync_response.status_code}"
            try:
                error_detail = sync_response.json()
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {sync_response.text}"
            return False, {"details": error_msg}

    except Exception as e:
        logger.error(f"❌ Source Cloud Storage sync error: {str(e)}")
        return False, {"details": str(e)}


    
# Main header
st.markdown('<h1 class="main-header">📊 Planogram Compliance</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Review System and Data Ingestion</p>', unsafe_allow_html=True)

# Create tabs - Thêm tab Deploy endpoint
tab1, tab2, tab3 = st.tabs(["📊 Label Studio", "🚀 Deploy endpoint", "🔍 Review",])


# Tab 1: RAG Data Ingestion
with tab1:
    # Layout: Two columns
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🖼️ Upload Images")

        # Project selection for upload
        if 'upload_projects' not in st.session_state:
            st.session_state.upload_projects = None
        if 'selected_upload_project' not in st.session_state:
            st.session_state.selected_upload_project = None
        if 'project_bucket_info' not in st.session_state:
            st.session_state.project_bucket_info = None
        if 'upload_bucket_name' not in st.session_state:
            st.session_state.upload_bucket_name = S3_BUCKET_NAME
        if 'upload_folder_prefix' not in st.session_state:
            st.session_state.upload_folder_prefix = "source-s3-storage"

        # Auto-load projects if not loaded
        if st.session_state.upload_projects is None:
            token = LABEL_STUDIO_API_TOKEN
            if token:
                headers = {"Authorization": f"Token {token}"}
                try:
                    response = requests.get(f"{LABEL_STUDIO_BASE_URL}/api/projects", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict) and 'results' in data:
                            st.session_state.upload_projects = data['results']
                        else:
                            st.session_state.upload_projects = data
                    else:
                        st.session_state.upload_projects = []
                except Exception as e:
                    st.session_state.upload_projects = []

        # Project selection
        if st.session_state.upload_projects:
            project_titles = [proj.get('title') or proj.get('name') or str(proj.get('id')) for proj in st.session_state.upload_projects]

            selected_project_title = st.selectbox(
                "Chọn Label Studio Project:",
                options=project_titles,
                index=None,
                placeholder="Choose project for upload...",
                key="upload_project_selectbox"
            )

            if selected_project_title:
                # Find selected project
                selected_project = None
                for proj in st.session_state.upload_projects:
                    if (proj.get('title') or proj.get('name') or str(proj.get('id'))) == selected_project_title:
                        selected_project = proj
                        break

                if selected_project:
                    st.session_state.selected_upload_project = selected_project

                    # Auto-get project storage info when project is selected
                    project_id = selected_project.get('id')
                    try:
                        storage_response = requests.get(
                            f"{LABEL_STUDIO_BASE_URL}/api/storages/s3",
                            headers={"Authorization": f"Token {LABEL_STUDIO_API_TOKEN}"},
                            params={"project": project_id}
                        )

                        if storage_response.status_code == 200:
                            storage_data = storage_response.json()
                            st.session_state.project_bucket_info = storage_data

                            # Update bucket info for upload
                            if storage_data and len(storage_data) > 0:
                                storage = storage_data[0]  # Get first storage
                                st.session_state.upload_bucket_name = storage.get('bucket', S3_BUCKET_NAME)
                                st.session_state.upload_folder_prefix = storage.get('prefix', 'source-s3-storage')
                        else:
                            # Reset to default if no storage found
                            st.session_state.upload_bucket_name = S3_BUCKET_NAME
                            st.session_state.upload_folder_prefix = "source-s3-storage"

                    except Exception as e:
                        # Reset to default on error
                        st.session_state.upload_bucket_name = S3_BUCKET_NAME
                        st.session_state.upload_folder_prefix = "source-s3-storage"
            else:
                # Reset when no project is selected
                st.session_state.selected_upload_project = None
                st.session_state.project_bucket_info = None
                st.session_state.upload_bucket_name = S3_BUCKET_NAME
                st.session_state.upload_folder_prefix = "source-s3-storage"

        # Only display configuration when project is selected
        if st.session_state.selected_upload_project:
            # Display current configuration based on selected project
            bucket_display = st.session_state.upload_bucket_name
            folder_display = st.session_state.upload_folder_prefix
            st.info(f"**S3 Bucket:** {bucket_display}/{folder_display}/")

            # Display selected project info
            project_name = st.session_state.selected_upload_project.get('title') or st.session_state.selected_upload_project.get('name')
            project_id = st.session_state.selected_upload_project.get('id')
            st.info(f"**Selected Project:** {project_name} (ID: {project_id})")

        # Upload Images section
        uploaded_images = st.file_uploader(
            "Choose image files",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="images_upload",
            help="Select images to upload to S3 and sync to Label Studio"
        )

        if uploaded_images:
            st.success(f"✅ Images selected: {len(uploaded_images)} files")
            
            # Show image preview (max 5 images)
            if len(uploaded_images) <= 5:
                st.markdown("**Preview:**")
                cols = st.columns(min(len(uploaded_images), 5))
                for i, img in enumerate(uploaded_images[:5]):
                    with cols[i]:
                        st.image(img, caption=img.name, width=100)
            else:
                st.info(f"Too many images to preview. Total: {len(uploaded_images)}")

        # Processing section
        st.markdown("---")

        # Upload button - only enable when both project and images are selected
        can_upload = uploaded_images and st.session_state.selected_upload_project
        upload_button = st.button(
            "Start Upload",
            type="primary",
            use_container_width=True,
            disabled=not can_upload
        )

        # Upload and sync process
        if upload_button:
            # Since button is only enabled when both conditions are met, we can proceed directly
            if uploaded_images and st.session_state.selected_upload_project:
                upload_results = {
                    'total_images': len(uploaded_images),
                    'successful_uploads': 0,
                    'successful_syncs': 0,
                    'failed_uploads': 0,
                    'failed_syncs': 0,
                    'errors': []
                }

                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, image_file in enumerate(uploaded_images):
                    progress = (i + 1) / len(uploaded_images)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {i+1}/{len(uploaded_images)}: {image_file.name}")

                    try:
                        # Step 1: Upload to S3 using project-specific bucket and folder
                        upload_bucket = st.session_state.upload_bucket_name
                        upload_prefix = st.session_state.upload_folder_prefix

                        s3_url, s3_key = upload_image_to_s3(
                            image_file,
                            upload_bucket,
                            folder_prefix=upload_prefix
                        )
                        upload_results['successful_uploads'] += 1
                        
                    except Exception as e:
                        upload_results['failed_uploads'] += 1
                        upload_results['errors'].append(f"Upload failed for {image_file.name} : {str(e)}")

                # Step 2: Trigger Label Studio Source Cloud Storage sync (once for all uploaded images)
                if upload_results['successful_uploads'] > 0:
                    try:
                        status_text.text("Triggering Label Studio Source Cloud Storage sync...")

                        # Use selected project (guaranteed to exist since button is only enabled when project is selected)
                        project_id = st.session_state.selected_upload_project.get('id')

                        sync_success, sync_response = trigger_labelstudio_storage_sync(
                            project_id,
                            LABEL_STUDIO_API_TOKEN,
                            LABEL_STUDIO_BASE_URL
                        )

                        if sync_success:
                            upload_results['successful_syncs'] = upload_results['successful_uploads']
                            upload_results['sync_info'] = sync_response
                        else:
                            upload_results['failed_syncs'] = upload_results['successful_uploads']
                            upload_results['errors'].append(f"Source Cloud Storage sync failed: {sync_response.get('details', 'Unknown error')}")

                    except Exception as e:
                        upload_results['failed_syncs'] = upload_results['successful_uploads']
                        upload_results['errors'].append(f"Source Cloud Storage sync exception: {str(e)}")

                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()

                # Display results
                st.markdown("---")
                st.subheader("📊 Upload Results")

                # Results statistics
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

                with col_stat1:
                    st.markdown(f'''
                    <div class="stat-box">
                        <div class="stat-number">{upload_results['total_images']}</div>
                        <div>Total Images</div>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_stat2:
                    st.markdown(f'''
                    <div class="stat-box">
                        <div class="stat-number" style="color: #28a745;">{upload_results['successful_uploads']}</div>
                        <div>S3 Uploads</div>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_stat3:
                    sync_status = "✅" if upload_results['successful_syncs'] > 0 else ("⚠️" if upload_results['successful_uploads'] > 0 else "❌")
                    st.markdown(f'''
                    <div class="stat-box">
                        <div class="stat-number" style="color: #007bff;">{sync_status}</div>
                        <div>LS Sync</div>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_stat4:
                    st.markdown(f'''
                    <div class="stat-box">
                        <div class="stat-number" style="color: #dc3545;">{len(upload_results['errors'])}</div>
                        <div>Errors</div>
                    </div>
                    ''', unsafe_allow_html=True)

                # Success/Error messages
                if upload_results['successful_syncs'] > 0:
                    sync_info = upload_results.get('sync_info', {})
                    storage_title = sync_info.get('storage_title', 'Source Cloud Storage')
                    storage_id = sync_info.get('storage_id', 'N/A')

                    st.markdown(f'''
                    <div class="result-success">
                        <h4>✅ Upload & Source Cloud Storage Sync Completed!</h4>
                        <p><strong>Successfully uploaded to S3:</strong> {upload_results['successful_uploads']}/{upload_results['total_images']} files</p>
                        <p><strong>Source Cloud Storage synced:</strong> {storage_title} (ID: {storage_id})</p>
                        <p><strong>Folder:</strong> {st.session_state.upload_folder_prefix}/</p>
                        <p><small>💡 Check Label Studio project for new tasks (may take a few moments to appear)</small></p>
                    </div>
                    ''', unsafe_allow_html=True)
                elif upload_results['successful_uploads'] > 0:
                    st.markdown(f'''
                    <div class="result-warning">
                        <h4>⚠️ Partial Success</h4>
                        <p><strong>Successfully uploaded to S3:</strong> {upload_results['successful_uploads']}/{upload_results['total_images']} files</p>
                        <p><strong>Source Cloud Storage sync failed:</strong> Images uploaded but sync trigger failed</p>
                        <p><strong>Folder:</strong> {st.session_state.upload_folder_prefix}/</p>
                        <p><small>💡 Try triggering Source Cloud Storage sync manually in Label Studio or wait for auto-scan</small></p>
                    </div>
                    ''', unsafe_allow_html=True)

                if upload_results['errors']:
                    st.markdown(f'''
                    <div class="result-error">
                        <h4>❌ Errors Found ({len(upload_results['errors'])})</h4>
                        <p>Some issues occurred during the process:</p>
                    </div>
                    ''', unsafe_allow_html=True)

                    with st.expander(f"❌ View Errors ({len(upload_results['errors'])})"):
                        for error in upload_results['errors']:
                            st.write(f"• {error}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.subheader("📥 Export Annotations")
        
        # Lấy token từ config nếu có
        token = LABEL_STUDIO_API_TOKEN
        
        if 'ls_projects' not in st.session_state:
            st.session_state.ls_projects = None
        if 'ls_error' not in st.session_state:
            st.session_state.ls_error = None
        
        # Khi vào tab, tự động fetch project nếu chưa có
        if st.session_state.ls_projects is None and st.session_state.ls_error is None:
            headers = {}
            if token:
                headers["Authorization"] = f"Token {token}"
            try:
                response = requests.get(f"{LABEL_STUDIO_BASE_URL}/api/projects", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'results' in data:
                        st.session_state.ls_projects = data['results']
                    else:
                        st.session_state.ls_projects = data
                    st.session_state.ls_error = None
                elif response.status_code == 401:
                    st.session_state.ls_projects = None
                    st.session_state.ls_error = "API Error 401: Authentication credentials were not provided. Vui lòng nhập API Token của bạn ở config.py!"
                else:
                    st.session_state.ls_projects = None
                    st.session_state.ls_error = f"API Error: {response.status_code} - {response.text}"
            except Exception as e:
                st.session_state.ls_projects = None
                st.session_state.ls_error = f"Exception: {str(e)}"
        
        # Hiển thị kết quả
        if st.session_state.ls_error:
            st.error(st.session_state.ls_error)
        elif st.session_state.ls_projects is not None:
            if isinstance(st.session_state.ls_projects, list) and st.session_state.ls_projects:
                project_titles = [proj.get('title') or proj.get('name') or str(proj.get('id')) for proj in st.session_state.ls_projects]
                
                selected_title = st.selectbox(
                    "Chọn Label Studio Project:",
                    options=project_titles,
                    index=None,
                    placeholder="Select a project...",
                    key="ls_project_selectbox"
                )
                
                # Khi chọn project, placeholder sẽ đổi thành tên project đã chọn
                if selected_title:
                    st.session_state.selected_project_title = selected_title
                
                # Lấy project đã chọn
                selected_project = None
                if hasattr(st.session_state, 'selected_project_title'):
                    for proj in st.session_state.ls_projects:
                        if (proj.get('title') or proj.get('name') or str(proj.get('id'))) == st.session_state.selected_project_title:
                            selected_project = proj
                            break
                
                if st.button("Start", type="primary", use_container_width=True):
                    if selected_project:
                        lambda_client = boto3.client('lambda', region_name='ap-southeast-1')
                        try:
                            with st.spinner("🔄 Exporting annotations and training..."):
                                response = lambda_client.invoke(
                                    FunctionName='MLPipelineStack-ExportAnnotationLambda2FBC2D72-MnrlgY50X7ZK',
                                    InvocationType='RequestResponse',
                                    Payload=json.dumps({"project_id": selected_project.get('id')})
                                )
                                result_payload = response['Payload'].read().decode('utf-8')
                                st.success(f"✅ Export completed! Lambda response: {result_payload}")
                        except Exception as e:
                            st.error(f"❌ Lỗi khi gọi Lambda: {str(e)}")
                    else:
                        st.warning("⚠️ Vui lòng chọn một project trước khi Export.")
            elif isinstance(st.session_state.ls_projects, list):
                st.info("📝 No projects found.")
            else:
                st.write(st.session_state.ls_projects)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Tab 2: Deploy endpoint
with tab2:
    # Create layout with Deploy endpoint in a corner (left column)
    col_deploy, col_empty = st.columns([1, 2])

    with col_deploy:
        st.subheader("Deploy Endpoint")

        # Initialize session state for selected folder
        if 'selected_folder' not in st.session_state:
            st.session_state.selected_folder = None
        if 'folders_cache' not in st.session_state:
            st.session_state.folders_cache = None
        if 'deploy_in_progress' not in st.session_state:
            st.session_state.deploy_in_progress = False

        # Auto-load folders when entering tab (similar to Label Studio projects)
        if st.session_state.folders_cache is None:
            with st.spinner("🔍 Loading folders from S3..."):
                st.session_state.folders_cache = get_s3_folders("uniben-data", "output_lambda/")

        folders = st.session_state.folders_cache

        # Display results similar to Label Studio tab
        if folders:
            # Selectbox for folder selection (similar to Label Studio project selection)
            selected_folder = st.selectbox(
                "Chọn folder từ S3 bucket:",
                options=folders,
                index=None,
                placeholder="Select a folder...",
                key="folder_selectbox"
            )

            # When folder is selected, update session state
            if selected_folder:
                st.session_state.selected_folder = selected_folder

            # Get selected folder
            current_folder = None
            if hasattr(st.session_state, 'selected_folder') and st.session_state.selected_folder:
                current_folder = st.session_state.selected_folder

            # Use button (similar to Export Labels button)
            deploy_button_disabled = st.session_state.deploy_in_progress
            deploy_button_text = "Deploying..." if deploy_button_disabled else "Deploy"

            if st.button(deploy_button_text, type="primary", use_container_width=True, disabled=deploy_button_disabled):
                if current_folder:
                    # Call Lambda function create_endpoint with folder name
                    # Configure Lambda client with extended timeout
                    lambda_client = boto3.client(
                        'lambda',
                        region_name='ap-southeast-1',
                        config=boto3.session.Config(
                            read_timeout=300,  # 5 minutes
                            connect_timeout=60,
                            retries={'max_attempts': 0}  # Disable retries to avoid confusion
                        )
                    )

                    try:
                        # Set deploy in progress
                        st.session_state.deploy_in_progress = True

                        with st.spinner("🔄 Creating endpoint... (This may take up to 5 minutes)"):
                            response = lambda_client.invoke(
                                FunctionName='create_endpoint',
                                InvocationType='RequestResponse',
                                Payload=json.dumps({"train_folder": current_folder})
                            )
                            result_payload = response['Payload'].read().decode('utf-8')

                            # Check if there was a function error
                            if 'FunctionError' in response:
                                st.error(f"❌ Lambda function error: {response['FunctionError']}")
                                st.error(f"Response: {result_payload}")
                            else:
                                st.success(f"✅ Endpoint created successfully!")

                                # Print the folder name and result
                                st.markdown("#### 📋 Deployment Result")
                                st.info(f"**Folder:** `{current_folder}`")
                                st.code(current_folder, language="text")

                                # Show Lambda response
                                with st.expander("📄 Lambda Response"):
                                    try:
                                        st.json(json.loads(result_payload))
                                    except json.JSONDecodeError:
                                        st.text(result_payload)

                    except Exception as e:
                        error_msg = str(e)
                        if "timeout" in error_msg.lower() or "read timeout" in error_msg.lower():
                            st.warning("⚠️ Request timeout - Lambda function may still be running")
                            st.info(f"""
                            **Lambda function đang chạy trong background:**
                            - Function: create_endpoint
                            - Folder: {current_folder}
                            - Thời gian chạy dự kiến: ~3-4 phút

                            💡 Bạn có thể check AWS Lambda console để xem trạng thái thực thi.
                            """)
                        else:
                            st.error(f"❌ Lỗi khi gọi Lambda create_endpoint: {error_msg}")

                        # Still show the folder name even if Lambda fails
                        st.markdown("#### 📋 Selected Folder")
                        st.info(f"**Folder:** `{current_folder}`")
                        st.code(current_folder, language="text")

                    finally:
                        # Reset deploy status regardless of success or failure
                        st.session_state.deploy_in_progress = False
                else:
                    st.warning("⚠️ Vui lòng chọn một folder trước khi sử dụng.")
        else:
            st.warning("⚠️ No folders found")
            st.info("💡 Check AWS credentials")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_empty:
        # Empty space or can be used for other content later
        st.markdown("")

# Tab 3: Review
with tab3:
    # Add CSS to remove scroll bars from Review tab and columns
    st.markdown("""
    <style>
    /* Remove scroll from main Review tab */
    div[data-testid="stTabContent"] {
        overflow: hidden !important;
        max-height: none !important;
    }

    /* Remove scroll from all columns in Review tab */
    div[data-testid="stTabContent"] div[data-testid="stVerticalBlock"] {
        overflow: hidden !important;
        max-height: none !important;
    }

    /* Remove scroll from column containers */
    div[data-testid="stTabContent"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] {
        overflow: hidden !important;
        max-height: none !important;
    }

    /* Ensure content fits naturally */
    div[data-testid="stTabContent"] .stMarkdown {
        overflow: visible !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 Review Pending Items")

    # Initialize session state
    if 'selected_image' not in st.session_state:
        st.session_state.selected_image = None
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Load pending review data
    try:
        conn = get_db_connection()
        pending_items = get_pending_review_items(conn)
        conn.close()

        # Display statistics
        if pending_items:
            # Calculate statistics
            total_items = len(pending_items)
            items_with_comments = len([item for item in pending_items if item.get('review_comment')])
            compliance_pass = len([item for item in pending_items if item.get('compliance_assessment')])
            compliance_fail = total_items - compliance_pass

            # Display stats in columns
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

            with stat_col1:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number">{total_items}</div>
                    <div>Total Items</div>
                </div>
                """, unsafe_allow_html=True)

            with stat_col2:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number" style="color: #28a745;">{compliance_pass}</div>
                    <div>Pass</div>
                </div>
                """, unsafe_allow_html=True)

            with stat_col3:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number" style="color: #dc3545;">{compliance_fail}</div>
                    <div>Fail</div>
                </div>
                """, unsafe_allow_html=True)

            with stat_col4:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-number" style="color: #6c757d;">{items_with_comments}</div>
                    <div>With Comments</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
        else:
            st.info("📝 No pending review items found")
            st.stop()

    except Exception as e:
        st.error(f"❌ Error loading pending review data: {str(e)}")
        st.stop()
    
    # Apply search filter
    search_term = st.session_state.search_term
    if search_term:
        filtered_items = [item for item in pending_items if search_term.lower() in item['image_name'].lower()]
    else:
        filtered_items = pending_items
    
    # Get total items count for display
    total_items = len(filtered_items)
    
    # 3-Column Layout
    col1, col2, col3 = st.columns([0.25, 0.35, 0.40])
    
    # Column 1: Image List
    with col1:
        st.markdown("#### 📷 Pending Images")
        st.caption(f"Total: {len(pending_items)} | Filtered: {total_items}")
        
        # Search box
        new_search = st.text_input(
            "🔍 Search", 
            value=st.session_state.search_term,
            placeholder="Enter image name...",
            key="search_input"
        )
        
        # Update search term if changed
        if new_search != st.session_state.search_term:
            st.session_state.search_term = new_search
            st.rerun()
        
        # Add CSS specific to Pending Images column only
        st.markdown("""
        <style>
        /* Only apply scroll to the Pending Images container */
        .pending-images-scroll {
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Create scrollable container using st.container with height
        with st.container(height=500):
            if filtered_items:
                # Display all filtered items in the scrollable container
                for item in filtered_items:
                    image_name = item['image_name']
                    compliance = item['compliance_assessment']
                    has_comment = bool(item.get('review_comment'))

                    # Check if selected
                    is_selected = st.session_state.selected_image == image_name

                    # Create status indicators
                    compliance_icon = "✅" if compliance else "❌"

                    # Create clickable button with conditional styling
                    if is_selected:
                        st.markdown(f"""
                        <div style="background-color: #2196f3; color: white; padding: 10px 16px;
                                    margin: 2px 0; border-radius: 6px; border: 1px solid #ddd;
                                    text-align: center; font-size: 16px;">
                            {image_name} {compliance_icon}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Create button with status indicators
                        button_text = f"{image_name} {compliance_icon}"
                        if st.button(button_text, key=f"btn_{image_name}", use_container_width=True):
                            st.session_state.selected_image = image_name
                            st.rerun()
            else:
                st.info("No items found")
    
    # Column 2: Image Display
    with col2:
        st.markdown("#### 🖼️ Image Preview")

        if st.session_state.selected_image:
            # Find selected item data
            selected_item = next((item for item in filtered_items
                                if item['image_name'] == st.session_state.selected_image), None)

            if selected_item:
                st.markdown(f"**📷 {selected_item['image_name']}**")

                # Display timestamp
                if selected_item['timestamp']:
                    st.caption(f"📅 {selected_item['timestamp']}")

                try:
                    # Display from S3 URL using presigned URL
                    if selected_item['s3_url']:
                        # Generate presigned URL for secure access
                        presigned_url = generate_presigned_url(selected_item['s3_url'])
                        st.image(presigned_url, use_container_width=True, caption="Image from S3")
                    else:
                        st.error("❌ No S3 URL available for this image")

                except Exception as e:
                    st.error(f"❌ Cannot display image: {str(e)}")
                    st.info("💡 Please check if the S3 URL is accessible or if AWS credentials are configured correctly")

            else:
                st.info("🔍 Selected image not found in current filter")
        else:
            st.markdown("""
            <div style="height: 300px; display: flex; align-items: center; justify-content: center;
                        background-color: #f0f0f0; border: 2px dashed #ccc; border-radius: 10px;">
                <p style="color: #666; text-align: center;">
                    📷 Select an image from the list<br>to view details
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Column 3: Analysis Results
    with col3:
        st.markdown("#### 📊 Analysis Results")

        if st.session_state.selected_image:
            # Find selected item data
            selected_item = next((item for item in filtered_items
                                if item['image_name'] == st.session_state.selected_image), None)

            if selected_item:
                # Display compliance status
                compliance = selected_item['compliance_assessment']
                compliance_text = "✅ Pass" if compliance else "❌ Fail"
                compliance_color = "#28a745" if compliance else "#dc3545"

                st.markdown(f"""
                <div style="background-color: {'#d4edda' if compliance else '#f8d7da'};
                            padding: 10px; border-radius: 5px; margin-bottom: 15px;
                            border: 1px solid {'#c3e6cb' if compliance else '#f5c6cb'};">
                    <strong>🎯 Compliance Status:</strong><br>
                    <span style="color: {compliance_color}; font-weight: bold; font-size: 1.1em;">{compliance_text}</span>
                </div>
                """, unsafe_allow_html=True)

                # Display product analysis
                if selected_item['product_count']:
                    try:
                        # Parse JSON product count data
                        if isinstance(selected_item['product_count'], str):
                            product_data = json.loads(selected_item['product_count'])
                        else:
                            product_data = selected_item['product_count']

                        # Display shelves analysis based on new format
                        if 'shelves' in product_data:
                            shelves = product_data['shelves']
                            total_shelves = len(shelves)

                            st.markdown(f"""
                            <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                                <strong>🗄️ Shelf Analysis</strong><br>
                                Total Shelves: <strong>{total_shelves}</strong>
                            </div>
                            """, unsafe_allow_html=True)

                            # Create shelves table
                            shelves_data = []
                            total_joco = 0
                            total_abben = 0
                            total_boncha = 0

                            for shelf in shelves:
                                shelf_number = shelf.get('shelf_number', 'N/A')
                                drinks = shelf.get('drinks', {})

                                joco_count = drinks.get('joco', 0)
                                abben_count = drinks.get('abben', 0)
                                boncha_count = drinks.get('boncha', 0)

                                shelves_data.append({
                                    'Shelf': f"Shelf {shelf_number}",
                                    'Joco': joco_count,
                                    'Abben': abben_count,
                                    'Boncha': boncha_count,
                                    'Total': joco_count + abben_count + boncha_count
                                })

                                total_joco += joco_count
                                total_abben += abben_count
                                total_boncha += boncha_count

                            # Display as DataFrame table
                            df_shelves = pd.DataFrame(shelves_data)
                            st.dataframe(df_shelves, use_container_width=True, hide_index=True)

                        else:
                            st.warning("⚠️ No shelves data found in the expected format")

                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON format: {str(e)}")

                        # Show raw data
                        with st.expander("📄 Raw Data"):
                            st.text(str(selected_item['product_count']))

                    except Exception as e:
                        st.error(f"❌ Error parsing product data: {str(e)}")

                        # Show raw data as fallback
                        with st.expander("📄 Raw Data"):
                            st.text(str(selected_item['product_count']))
                else:
                    st.warning("⚠️ No product analysis data available")

                # Display review comment if exists
                if selected_item.get('review_comment'):
                    st.markdown("#### 💬 Review Comment")
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;
                                margin-bottom: 15px; border-left: 4px solid #007bff;">
                        {selected_item['review_comment']}
                    </div>
                    """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div style="height: 200px; display: flex; align-items: center; justify-content: center;
                        background-color: #fff3cd; border: 2px dashed #ffc107; border-radius: 10px;">
                <p style="color: #856404; text-align: center;">
                    📊 Select an image to view<br>analysis results
                </p>
            </div>
            """, unsafe_allow_html=True)


# Footer
st.markdown("---")
