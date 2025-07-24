"""
Planogram Compliance - Main Streamlit Application
Review System and Image Import with Label Studio Integration
"""
import streamlit as st
import logging
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# Import application services
from app.config import config
from app.services.data_ops import DatabaseService, LambdaService, generate_presigned_url
from app.services.labelstudio_service import LabelStudioService
from app.services.storage_service import ImageProcessor

# Setup logging
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Planogram Compliance",
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        padding: 20px 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 20px;
    }
    .section-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    .result-success {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .result-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #dc3545;
        margin: 10px 0;
    }
    .result-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    .stat-card {
        text-align: center;
        padding: 20px;
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2.5em;
        font-weight: bold;
        color: #2E86AB;
        margin-bottom: 5px;
    }
    .stat-label {
        font-size: 0.9em;
        color: #6c757d;
        text-transform: uppercase;
    }
    .project-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin: 5px 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    .project-card:hover {
        border-color: #2E86AB;
        box-shadow: 0 2px 8px rgba(46, 134, 171, 0.15);
    }
    .project-selected {
        border-color: #2E86AB !important;
        background-color: #e8f4f8 !important;
    }
    .upload-area {
        border: 2px dashed #dee2e6;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        background-color: #ffffff;
        transition: all 0.3s;
    }
    .upload-area:hover {
        border-color: #2E86AB;
        background-color: #f8fcfd;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'ls_projects' not in st.session_state:
        st.session_state.ls_projects = None
    if 'ls_error' not in st.session_state:
        st.session_state.ls_error = None
    if 'selected_image' not in st.session_state:
        st.session_state.selected_image = None
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ""

def load_label_studio_projects():
    """Load Label Studio projects with caching"""
    if st.session_state.ls_projects is None and st.session_state.ls_error is None:
        with st.spinner("🔍 Loading Label Studio projects..."):
            ls_service = LabelStudioService()
            result = ls_service.get_projects()
            
            if result['success']:
                st.session_state.ls_projects = result['projects']
                st.session_state.ls_error = None
            else:
                st.session_state.ls_projects = None
                st.session_state.ls_error = result['error']

def render_review_tab():
    """Render Review tab content"""
    st.markdown("### 🔍 Review Pending Items")
    
    try:
        # Load pending review data
        conn = DatabaseService.get_connection()
        pending_items = DatabaseService.get_pending_review_items(conn)
        conn.close()
        
        if not pending_items:
            st.info("📝 No pending review items found")
            return
        
        # Display statistics
        total_items = len(pending_items)
        items_with_comments = len([item for item in pending_items if item.get('review_comment')])
        compliance_pass = len([item for item in pending_items if item.get('compliance_assessment')])
        compliance_fail = total_items - compliance_pass
        
        # Stats grid
        st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
        
        stats_cols = st.columns(4)
        
        with stats_cols[0]:
            st.markdown(f'''
            <div class="stat-card">
                <div class="stat-number">{total_items}</div>
                <div class="stat-label">Total Items</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with stats_cols[1]:
            st.markdown(f'''
            <div class="stat-card">
                <div class="stat-number" style="color: #28a745;">{compliance_pass}</div>
                <div class="stat-label">Compliance Pass</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with stats_cols[2]:
            st.markdown(f'''
            <div class="stat-card">
                <div class="stat-number" style="color: #dc3545;">{compliance_fail}</div>
                <div class="stat-label">Compliance Fail</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with stats_cols[3]:
            st.markdown(f'''
            <div class="stat-card">
                <div class="stat-number" style="color: #6c757d;">{items_with_comments}</div>
                <div class="stat-label">With Comments</div>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Filter items based on search
        search_term = st.session_state.search_term
        if search_term:
            filtered_items = [item for item in pending_items 
                            if search_term.lower() in item['image_name'].lower()]
        else:
            filtered_items = pending_items
        
        # Three-column layout
        col1, col2, col3 = st.columns([0.25, 0.35, 0.40])
        
        # Column 1: Image List
        with col1:
            st.markdown("#### 📷 Pending Images")
            st.caption(f"Total: {len(pending_items)} | Filtered: {len(filtered_items)}")
            
            # Search box
            new_search = st.text_input(
                "🔍 Search", 
                value=st.session_state.search_term,
                placeholder="Enter image name...",
                key="search_input"
            )
            
            if new_search != st.session_state.search_term:
                st.session_state.search_term = new_search
                st.rerun()
            
            # Scrollable image list
            with st.container(height=500):
                if filtered_items:
                    for item in filtered_items:
                        image_name = item['image_name']
                        compliance = item['compliance_assessment']
                        
                        # Status indicator
                        status_icon = "✅" if compliance else "❌"
                        
                        # Check if selected
                        is_selected = st.session_state.selected_image == image_name
                        
                        if is_selected:
                            st.markdown(f'''
                            <div style="background-color: #2196f3; color: white; padding: 10px 16px;
                                        margin: 2px 0; border-radius: 6px; text-align: center;">
                                {image_name} {status_icon}
                            </div>
                            ''', unsafe_allow_html=True)
                        else:
                            if st.button(f"{image_name} {status_icon}", 
                                       key=f"btn_{image_name}", 
                                       use_container_width=True):
                                st.session_state.selected_image = image_name
                                st.rerun()
                else:
                    st.info("No items found")
        
        # Column 2: Image Display
        with col2:
            st.markdown("#### 🖼️ Image Preview")
            
            if st.session_state.selected_image:
                selected_item = next((item for item in filtered_items
                                    if item['image_name'] == st.session_state.selected_image), None)
                
                if selected_item:
                    st.markdown(f"**📷 {selected_item['image_name']}**")
                    
                    if selected_item['timestamp']:
                        st.caption(f"📅 {selected_item['timestamp']}")
                    
                    try:
                        if selected_item['s3_url']:
                            presigned_url = generate_presigned_url(selected_item['s3_url'])
                            st.image(presigned_url, use_container_width=True)
                        else:
                            st.error("❌ No S3 URL available")
                    except Exception as e:
                        st.error(f"❌ Cannot display image: {str(e)}")
                else:
                    st.info("🔍 Selected image not found in current filter")
            else:
                st.markdown('''
                <div style="height: 300px; display: flex; align-items: center; justify-content: center;
                            background-color: #f0f0f0; border: 2px dashed #ccc; border-radius: 10px;">
                    <p style="color: #666; text-align: center;">
                        📷 Select an image from the list<br>to view details
                    </p>
                </div>
                ''', unsafe_allow_html=True)
        
        # Column 3: Analysis Results
        with col3:
            st.markdown("#### 📊 Analysis Results")
            
            if st.session_state.selected_image:
                selected_item = next((item for item in filtered_items
                                    if item['image_name'] == st.session_state.selected_image), None)
                
                if selected_item:
                    # Compliance status
                    compliance = selected_item['compliance_assessment']
                    compliance_text = "✅ Pass" if compliance else "❌ Fail"
                    compliance_color = "#28a745" if compliance else "#dc3545"
                    
                    st.markdown(f'''
                    <div class="result-{'success' if compliance else 'error'}">
                        <strong>🎯 Compliance Status:</strong><br>
                        <span style="font-size: 1.2em;">{compliance_text}</span>
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    # Product analysis
                    if selected_item['product_count']:
                        try:
                            # Parse product data
                            if isinstance(selected_item['product_count'], str):
                                product_data = json.loads(selected_item['product_count'])
                            else:
                                product_data = selected_item['product_count']
                            
                            # Display shelf analysis
                            if 'shelves' in product_data:
                                shelves = product_data['shelves']
                                
                                st.markdown(f'''
                                <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 15px 0;">
                                    <strong>🗄️ Shelf Analysis</strong><br>
                                    Total Shelves: <strong>{len(shelves)}</strong>
                                </div>
                                ''', unsafe_allow_html=True)
                                
                                # Create shelves table
                                shelves_data = []
                                for shelf in shelves:
                                    shelf_number = shelf.get('shelf_number', 'N/A')
                                    drinks = shelf.get('drinks', {})
                                    
                                    shelves_data.append({
                                        'Shelf': f"Shelf {shelf_number}",
                                        'Joco': drinks.get('joco', 0),
                                        'Abben': drinks.get('abben', 0),
                                        'Boncha': drinks.get('boncha', 0),
                                        'Total': sum(drinks.values())
                                    })
                                
                                # Display table
                                df_shelves = pd.DataFrame(shelves_data)
                                st.dataframe(df_shelves, use_container_width=True, hide_index=True)
                            else:
                                st.warning("⚠️ No shelves data found")
                                
                        except json.JSONDecodeError:
                            st.error("❌ Invalid JSON format in product data")
                        except Exception as e:
                            st.error(f"❌ Error parsing product data: {str(e)}")
                    else:
                        st.warning("⚠️ No product analysis data available")
                    
                    # Review comment
                    if selected_item.get('review_comment'):
                        st.markdown("#### 💬 Review Comment")
                        st.markdown(f'''
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;
                                    border-left: 4px solid #007bff;">
                            {selected_item['review_comment']}
                        </div>
                        ''', unsafe_allow_html=True)
            else:
                st.markdown('''
                <div style="height: 200px; display: flex; align-items: center; justify-content: center;
                            background-color: #fff3cd; border: 2px dashed #ffc107; border-radius: 10px;">
                    <p style="color: #856404; text-align: center;">
                        📊 Select an image to view<br>analysis results
                    </p>
                </div>
                ''', unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Error loading review data: {str(e)}")
        logger.error(f"Review tab error: {str(e)}")

def render_import_tab():
    """Render Import & Processing tab content"""
    st.markdown("### 📥 Import & Processing")
    
    # Load Label Studio projects
    load_label_studio_projects()
    
    # Section 1: Project Selection
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("#### 🎯 Select Label Studio Project")
    
    if st.session_state.ls_error:
        st.error(f"❌ {st.session_state.ls_error}")
        if st.button("🔄 Retry Connection", type="secondary"):
            st.session_state.ls_projects = None
            st.session_state.ls_error = None
            st.rerun()
    
    elif st.session_state.ls_projects:
        # Display projects in a grid
        if st.session_state.ls_projects:
            cols = st.columns(3)
            for i, project in enumerate(st.session_state.ls_projects):
                col_idx = i % 3
                with cols[col_idx]:
                    project_id = project.get('id')
                    project_title = project.get('title') or project.get('name') or f"Project {project_id}"
                    project_description = project.get('description', '')[:100]
                    
                    # Check if selected
                    is_selected = (st.session_state.selected_project and 
                                 st.session_state.selected_project['id'] == project_id)
                    
                    card_class = "project-card project-selected" if is_selected else "project-card"
                    
                    if st.button(
                        f"📁 {project_title}\n{project_description}...",
                        key=f"project_{project_id}",
                        use_container_width=True
                    ):
                        st.session_state.selected_project = project
                        st.rerun()
            
            # Display selected project info
            if st.session_state.selected_project:
                project = st.session_state.selected_project
                st.success(f"✅ Selected: **{project.get('title', 'Unknown')}** (ID: {project.get('id')})")
        else:
            st.warning("No Label Studio projects found")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 2: Image Upload
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("#### 📷 Upload Images")
    st.markdown("*Supported formats: PNG, JPG, JPEG*")
    
    uploaded_images = st.file_uploader(
        "Choose image files",
        type=config.SUPPORTED_IMAGE_FORMATS,
        accept_multiple_files=True,
        key="images_upload",
        help=f"Upload images for Label Studio annotation. Max size: {config.MAX_FILE_SIZE_MB}MB per file"
    )
    
    if uploaded_images:
        st.success(f"✅ {len(uploaded_images)} images uploaded")
        
        # Quick validation summary
        total_size = sum(img.size for img in uploaded_images) / (1024 * 1024)  # MB
        st.info(f"📊 Total size: {total_size:.2f} MB | Average: {total_size/len(uploaded_images):.2f} MB per image")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 3: Import & Sync
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("#### 🚀 Import & Sync")
    
    # Check if ready to process
    can_process = (st.session_state.selected_project is not None and 
                   uploaded_images is not None and 
                   len(uploaded_images) > 0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button(
            "🚀 Import Images to Label Studio",
            type="primary",
            disabled=not can_process,
            use_container_width=True
        ):
            if can_process:
                process_import_workflow(uploaded_images, st.session_state.selected_project)
            else:
                st.warning("⚠️ Please select a project and upload images first")
    
    if not can_process:
        missing_items = []
        if not st.session_state.selected_project:
            missing_items.append("Label Studio project")
        if not uploaded_images:
            missing_items.append("Images")
        
        st.info(f"📋 Still needed: {', '.join(missing_items)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 4: Export Labels
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("#### 📤 Export Labels")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button(
            "📤 Export Labels via Lambda",
            type="secondary",
            disabled=not st.session_state.selected_project,
            use_container_width=True
        ):
            if st.session_state.selected_project:
                process_export_workflow(st.session_state.selected_project)
            else:
                st.warning("⚠️ Please select a project first")
    
    st.markdown('</div>', unsafe_allow_html=True)

def process_import_workflow(uploaded_images: List, selected_project: Dict):
    """Process the import workflow"""
    try:
        project_id = selected_project['id']
        project_title = selected_project.get('title', 'Unknown')
        
        st.info(f"🔄 Starting import process for project: **{project_title}**")
        
        # Initialize processor
        processor = ImageProcessor()
        
        # Show progress
        with st.spinner("Processing images and syncing with Label Studio..."):
            # Run workflow
            results = processor.run_full_workflow(uploaded_images, project_id)
        
        # Display results
        st.markdown("---")
        st.markdown("### 📊 Import Results")
        
        # Statistics
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("Total Images", results['total_images'])
        
        with cols[1]:
            st.metric("Uploaded to S3", results['upload_successful'])
        
        with cols[2]:
            st.metric("Label Studio Tasks", results['task_count'])
        
        with cols[3]:
            st.metric("Processing Time", f"{results['processing_time']}s")
        
        # Success/Error messages
        if results['import_successful']:
            st.markdown(f'''
            <div class="result-success">
                <h4>🎉 Import Completed Successfully!</h4>
                <p><strong>✅ {results['upload_successful']}</strong> images uploaded to S3</p>
                <p><strong>🎯 {results['task_count']}</strong> tasks created in Label Studio</p>
                <p><strong>📁 S3 Folder:</strong> {results['s3_folder']}</p>
                <p><strong>⏱️ Total Time:</strong> {results['processing_time']} seconds</p>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="result-warning">
                <h4>⚠️ Import Partially Completed</h4>
                <p><strong>✅ {results['upload_successful']}</strong> images uploaded to S3</p>
                <p><strong>❌</strong> Label Studio sync failed</p>
                <p>Images are safely stored in S3 and can be manually imported to Label Studio</p>
            </div>
            ''', unsafe_allow_html=True)
        
        # Show errors if any
        if results['errors']:
            with st.expander(f"⚠️ Issues Found ({len(results['errors'])})", expanded=False):
                for error in results['errors']:
                    st.write(f"• {error}")
        
    except Exception as e:
        st.markdown(f'''
        <div class="result-error">
            <h4>❌ Import Failed</h4>
            <p>An unexpected error occurred: {str(e)}</p>
        </div>
        ''', unsafe_allow_html=True)
        logger.error(f"Import workflow error: {str(e)}")

def process_export_workflow(selected_project: Dict):
    """Process the export workflow"""
    try:
        project_id = selected_project['id']
        project_title = selected_project.get('title', 'Unknown')
        
        st.info(f"🔄 Starting export process for project: **{project_title}**")
        
        # Initialize Lambda service
        lambda_service = LambdaService()
        
        # Show progress
        with st.spinner("Triggering label export via Lambda..."):
            result = lambda_service.trigger_export_labels(project_id)
        
        # Display results
        if result['success']:
            st.markdown(f'''
            <div class="result-success">
                <h4>✅ Export Triggered Successfully!</h4>
                <p><strong>Project:</strong> {project_title}</p>
                <p><strong>Status Code:</strong> {result['status_code']}</p>
                <p><strong>Response:</strong> {result['response']}</p>
            </div>
            ''', unsafe_allow_html=True)
        else:
            error_msg = result.get('error', 'Unknown error')
            st.markdown(f'''
            <div class="result-error">
                <h4>❌ Export Failed</h4>
                <p><strong>Project:</strong> {project_title}</p>
                <p><strong>Error:</strong> {error_msg}</p>
            </div>
            ''', unsafe_allow_html=True)
        
    except Exception as e:
        st.markdown(f'''
        <div class="result-error">
            <h4>❌ Export Failed</h4>
            <p>An unexpected error occurred: {str(e)}</p>
        </div>
        ''', unsafe_allow_html=True)
        logger.error(f"Export workflow error: {str(e)}")

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Main header
    st.markdown('<h1 class="main-header">📊 Planogram Compliance</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Review System and Label Studio Integration</p>', unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔍 Review", "📥 Import & Processing"])
    
    # Render tabs
    with tab1:
        render_review_tab()
    
    with tab2:
        render_import_tab()
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🔧 <strong>{config.APP_NAME}</strong> v{config.APP_VERSION} | 
        📝 Configure settings in <code>.env</code> file | 
        🐛 Debug mode: {'ON' if config.DEBUG else 'OFF'}</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()