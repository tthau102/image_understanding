"""
Import & Processing tab component for Planogram Compliance application.
"""
import streamlit as st
from typing import List, Dict, Optional
from app.config import config
from app.services.labelstudio_service import LabelStudioService
from app.services.storage_service import ImageProcessor
from app.services.data_ops import LambdaService

def load_label_studio_projects():
    """Load Label Studio projects with caching and error handling"""
    if st.session_state.get('ls_projects') is None and st.session_state.get('ls_error') is None:
        with st.spinner("🔍 Connecting to Label Studio..."):
            ls_service = LabelStudioService()
            result = ls_service.get_projects()
            
            if result['success']:
                st.session_state.ls_projects = result['projects']
                st.session_state.ls_error = None
            else:
                st.session_state.ls_projects = None
                st.session_state.ls_error = result['error']

def render_project_selection():
    """Render modern project selection interface"""
    st.markdown("""
    <div class="section-header">
        <h3>🎯 Select Label Studio Project</h3>
        <p>Choose the project where you want to import images for annotation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load projects
    load_label_studio_projects()
    
    if st.session_state.get('ls_error'):
        # Error state with retry option
        st.markdown(f"""
        <div class="error-card">
            <div class="error-icon">⚠️</div>
            <div class="error-content">
                <h4>Connection Failed</h4>
                <p>{st.session_state.ls_error}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Retry Connection", type="primary", use_container_width=True):
                st.session_state.ls_projects = None
                st.session_state.ls_error = None
                st.rerun()
        
        return False
    
    elif st.session_state.get('ls_projects'):
        projects = st.session_state.ls_projects
        
        if projects:
            # Display projects in modern card grid
            st.markdown("""
            <style>
            .project-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 16px;
                margin: 20px 0;
            }
            
            .project-card {
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                border: 2px solid #e9ecef;
                border-radius: 16px;
                padding: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .project-card:hover {
                border-color: #0066cc;
                transform: translateY(-4px);
                box-shadow: 0 8px 25px rgba(0, 102, 204, 0.15);
            }
            
            .project-card.selected {
                border-color: #0066cc;
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                box-shadow: 0 8px 25px rgba(0, 102, 204, 0.2);
            }
            
            .project-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #0066cc, #00b4d8);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .project-card:hover::before,
            .project-card.selected::before {
                opacity: 1;
            }
            
            .project-header {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
            }
            
            .project-icon {
                font-size: 24px;
                margin-right: 12px;
            }
            
            .project-title {
                font-size: 18px;
                font-weight: 600;
                color: #1a1a1a;
                margin: 0;
            }
            
            .project-id {
                font-size: 12px;
                color: #6c757d;
                background: #f8f9fa;
                padding: 2px 8px;
                border-radius: 12px;
                margin-left: auto;
            }
            
            .project-description {
                color: #495057;
                font-size: 14px;
                line-height: 1.4;
                margin-bottom: 16px;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .project-meta {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: #6c757d;
            }
            
            .selected-indicator {
                color: #0066cc;
                font-weight: 600;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create project cards
            cols = st.columns(2)  # 2 columns for better layout
            
            for i, project in enumerate(projects):
                col_idx = i % 2
                
                with cols[col_idx]:
                    project_id = project.get('id')
                    project_title = project.get('title') or project.get('name') or f"Project {project_id}"
                    project_description = project.get('description', 'No description available')[:150]
                    
                    # Check if selected
                    is_selected = (st.session_state.get('selected_project') and 
                                 st.session_state.selected_project['id'] == project_id)
                    
                    # Create button for project selection
                    button_key = f"project_btn_{project_id}"
                    
                    if st.button(
                        f"📁 {project_title}",
                        key=button_key,
                        help=f"Select project: {project_title}",
                        use_container_width=True
                    ):
                        st.session_state.selected_project = project
                        st.rerun()
                    
                    # Show project card with selection state
                    card_class = "project-card selected" if is_selected else "project-card"
                    
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div class="project-header">
                            <span class="project-icon">📁</span>
                            <h4 class="project-title">{project_title}</h4>
                            <span class="project-id">ID: {project_id}</span>
                        </div>
                        <div class="project-description">
                            {project_description}...
                        </div>
                        <div class="project-meta">
                            <span>📊 Ready for import</span>
                            {f'<span class="selected-indicator">✅ Selected</span>' if is_selected else '<span>Click to select</span>'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Show selected project info
            if st.session_state.get('selected_project'):
                project = st.session_state.selected_project
                st.success(f"✅ **Selected Project:** {project.get('title', 'Unknown')} (ID: {project.get('id')})")
                return True
            else:
                st.info("👆 Select a project above to continue")
                return False
        else:
            st.warning("📂 No Label Studio projects found")
            return False
    else:
        # Loading state
        with st.spinner("🔄 Loading projects..."):
            st.info("⏳ Connecting to Label Studio...")
        return False

def render_image_upload():
    """Render modern image upload interface"""
    st.markdown("""
    <div class="section-header">
        <h3>📷 Upload Images</h3>
        <p>Upload images that will be imported to Label Studio for annotation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Custom CSS for upload area
    st.markdown("""
    <style>
    .upload-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px dashed #6c757d;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        margin: 20px 0;
        transition: all 0.3s ease;
    }
    
    .upload-container:hover {
        border-color: #0066cc;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        transform: translateY(-2px);
    }
    
    .upload-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }
    
    .info-card {
        background: white;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        text-align: center;
    }
    
    .info-icon {
        font-size: 24px;
        margin-bottom: 8px;
    }
    
    .info-title {
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 4px;
    }
    
    .info-text {
        font-size: 14px;
        color: #6c757d;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # File uploader with enhanced styling
    uploaded_images = st.file_uploader(
        "",
        type=config.SUPPORTED_IMAGE_FORMATS,
        accept_multiple_files=True,
        key="images_upload",
        help=f"Supported formats: {', '.join(config.SUPPORTED_IMAGE_FORMATS).upper()}. Max size: {config.MAX_FILE_SIZE_MB}MB per file",
        label_visibility="collapsed"
    )
    
    if uploaded_images:
        # Success state with file info
        total_size = sum(img.size for img in uploaded_images) / (1024 * 1024)  # MB
        avg_size = total_size / len(uploaded_images)
        
        st.markdown(f"""
        <div class="upload-success">
            <div class="success-header">
                <span class="success-icon">✅</span>
                <span class="success-text">Successfully uploaded {len(uploaded_images)} images</span>
            </div>
            <div class="upload-info">
                <div class="info-card">
                    <div class="info-icon">📊</div>
                    <div class="info-title">Total Size</div>
                    <div class="info-text">{total_size:.2f} MB</div>
                </div>
                <div class="info-card">
                    <div class="info-icon">📏</div>
                    <div class="info-title">Average Size</div>
                    <div class="info-text">{avg_size:.2f} MB</div>
                </div>
                <div class="info-card">
                    <div class="info-icon">🗂️</div>
                    <div class="info-title">File Count</div>
                    <div class="info-text">{len(uploaded_images)} files</div>
                </div>
                <div class="info-card">
                    <div class="info-icon">✨</div>
                    <div class="info-title">Status</div>
                    <div class="info-text">Ready to import</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        return uploaded_images
    else:
        # Upload instructions
        st.markdown(f"""
        <div class="upload-container">
            <div style="font-size: 48px; margin-bottom: 16px;">📸</div>
            <h3>Drag and drop images here</h3>
            <p>or click to browse your files</p>
            <div class="upload-info">
                <div class="info-card">
                    <div class="info-icon">📋</div>
                    <div class="info-title">Supported Formats</div>
                    <div class="info-text">{', '.join(config.SUPPORTED_IMAGE_FORMATS).upper()}</div>
                </div>
                <div class="info-card">
                    <div class="info-icon">⚖️</div>
                    <div class="info-title">Max File Size</div>
                    <div class="info-text">{config.MAX_FILE_SIZE_MB} MB</div>
                </div>
                <div class="info-card">
                    <div class="info-icon">🚀</div>
                    <div class="info-title">Multiple Files</div>
                    <div class="info-text">Upload in batches</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        return None

def render_import_actions(can_process: bool, uploaded_images, selected_project):
    """Render import and export action buttons"""
    st.markdown("""
    <div class="section-header">
        <h3>🚀 Import & Export Actions</h3>
        <p>Process your images and manage Label Studio integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Import button with status
        st.markdown("#### 📥 Import to Label Studio")
        
        if can_process:
            st.markdown("""
            <div class="action-ready">
                <span class="ready-icon">✅</span>
                <span>Ready to import {len(uploaded_images)} images</span>
            </div>
            """.format(len=len), unsafe_allow_html=True)
        else:
            missing_items = []
            if not selected_project:
                missing_items.append("Label Studio project")
            if not uploaded_images:
                missing_items.append("Images")
            
            st.markdown(f"""
            <div class="action-pending">
                <span class="pending-icon">⏳</span>
                <span>Missing: {', '.join(missing_items)}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Import button
        if st.button(
            "🚀 Import Images to Label Studio",
            type="primary",
            disabled=not can_process,
            use_container_width=True,
            help="Upload images to S3 and sync with selected Label Studio project"
        ):
            if can_process:
                process_import_workflow(uploaded_images, selected_project)
    
    with col2:
        # Export button
        st.markdown("#### 📤 Export Annotations")
        
        if selected_project:
            st.markdown("""
            <div class="action-ready">
                <span class="ready-icon">✅</span>
                <span>Project selected for export</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="action-pending">
                <span class="pending-icon">⏳</span>
                <span>Select a project first</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Export button
        if st.button(
            "📤 Export Labels via Lambda",
            type="secondary",
            disabled=not selected_project,
            use_container_width=True,
            help="Trigger Lambda function to export annotations from Label Studio"
        ):
            if selected_project:
                process_export_workflow(selected_project)

def process_import_workflow(uploaded_images: List, selected_project: Dict):
    """Process the import workflow with modern UI feedback"""
    try:
        project_id = selected_project['id']
        project_title = selected_project.get('title', 'Unknown')
        
        # Progress header
        st.markdown(f"""
        <div class="process-header">
            <h3>🔄 Processing Import</h3>
            <p>Importing {len(uploaded_images)} images to project: <strong>{project_title}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Progress steps
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        # Initialize processor
        processor = ImageProcessor()
        
        # Step-by-step processing with progress updates
        status_placeholder.info("🔍 Validating images...")
        progress_bar.progress(10)
        
        status_placeholder.info("☁️ Uploading to S3...")
        progress_bar.progress(30)
        
        status_placeholder.info("🔗 Syncing with Label Studio...")
        progress_bar.progress(60)
        
        # Run workflow
        results = processor.run_full_workflow(uploaded_images, project_id)
        
        progress_bar.progress(100)
        status_placeholder.success("✅ Processing completed!")
        
        # Results section
        st.markdown("---")
        st.markdown("### 📊 Import Results")
        
        # Results cards
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("📸 Total Images", results['total_images'])
        
        with cols[1]:
            st.metric("☁️ Uploaded to S3", results['upload_successful'])
        
        with cols[2]:
            st.metric("🎯 Label Studio Tasks", results['task_count'])
        
        with cols[3]:
            st.metric("⏱️ Processing Time", f"{results['processing_time']}s")
        
        # Success/Error feedback
        if results['import_successful']:
            st.markdown(f"""
            <div class="result-success-card">
                <div class="result-header">
                    <span class="result-icon">🎉</span>
                    <h4>Import Completed Successfully!</h4>
                </div>
                <div class="result-details">
                    <p><strong>✅ {results['upload_successful']}</strong> images uploaded to S3</p>
                    <p><strong>🎯 {results['task_count']}</strong> tasks created in Label Studio</p>
                    <p><strong>📁 S3 Folder:</strong> <code>{results['s3_folder']}</code></p>
                    <p><strong>⏱️ Total Time:</strong> {results['processing_time']} seconds</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-warning-card">
                <div class="result-header">
                    <span class="result-icon">⚠️</span>
                    <h4>Import Partially Completed</h4>
                </div>
                <div class="result-details">
                    <p><strong>✅ {results['upload_successful']}</strong> images uploaded to S3</p>
                    <p><strong>❌</strong> Label Studio sync failed</p>
                    <p>Images are safely stored in S3 and can be manually imported to Label Studio</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Show errors if any
        if results['errors']:
            with st.expander(f"⚠️ Issues Found ({len(results['errors'])})", expanded=False):
                for error in results['errors']:
                    st.write(f"• {error}")
        
    except Exception as e:
        st.markdown(f"""
        <div class="result-error-card">
            <div class="result-header">
                <span class="result-icon">❌</span>
                <h4>Import Failed</h4>
            </div>
            <div class="result-details">
                <p>An unexpected error occurred: {str(e)}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def process_export_workflow(selected_project: Dict):
    """Process the export workflow with modern UI feedback"""
    try:
        project_id = selected_project['id']
        project_title = selected_project.get('title', 'Unknown')
        
        st.markdown(f"""
        <div class="process-header">
            <h3>🔄 Processing Export</h3>
            <p>Exporting annotations from project: <strong>{project_title}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize Lambda service
        lambda_service = LambdaService()
        
        # Show progress
        with st.spinner("🚀 Triggering export via Lambda..."):
            result = lambda_service.trigger_export_labels(project_id)
        
        # Display results
        if result['success']:
            st.markdown(f"""
            <div class="result-success-card">
                <div class="result-header">
                    <span class="result-icon">✅</span>
                    <h4>Export Triggered Successfully!</h4>
                </div>
                <div class="result-details">
                    <p><strong>Project:</strong> {project_title}</p>
                    <p><strong>Status Code:</strong> {result['status_code']}</p>
                    <p><strong>Response:</strong> <code>{result['response']}</code></p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            error_msg = result.get('error', 'Unknown error')
            st.markdown(f"""
            <div class="result-error-card">
                <div class="result-header">
                    <span class="result-icon">❌</span>
                    <h4>Export Failed</h4>
                </div>
                <div class="result-details">
                    <p><strong>Project:</strong> {project_title}</p>
                    <p><strong>Error:</strong> {error_msg}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
    except Exception as e:
        st.markdown(f"""
        <div class="result-error-card">
            <div class="result-header">
                <span class="result-icon">❌</span>
                <h4>Export Failed</h4>
            </div>
            <div class="result-details">
                <p>An unexpected error occurred: {str(e)}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_import_tab():
    """Main render function for Import & Processing tab"""
    # Tab header
    st.markdown("""
    <div class="tab-header">
        <h2>📥 Import & Processing</h2>
        <p>Upload images and sync with Label Studio for annotation projects</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Project selection section
    has_project = render_project_selection()
    
    st.markdown("---")
    
    # Image upload section
    uploaded_images = render_image_upload()
    
    st.markdown("---")
    
    # Check if ready to process
    can_process = (has_project and uploaded_images is not None and len(uploaded_images) > 0)
    
    # Import and export actions
    render_import_actions(can_process, uploaded_images, st.session_state.get('selected_project'))