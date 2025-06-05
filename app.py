import streamlit as st
import logging
from rag_processor import RAGProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    layout="wide", 
    page_title="RAG Data Ingestion",
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
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">📊 RAG Data Ingestion</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Upload CSV and Images for Processing</p>', unsafe_allow_html=True)

# Layout: Two columns for upload, full width for results
col1, col2 = st.columns([1, 1])

# Upload CSV section
with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📄 Upload CSV File")
    st.markdown("*Required columns: image_name, description*")
    
    uploaded_csv = st.file_uploader(
        "Choose CSV file", 
        type=["csv"], 
        key="csv_upload",
        help="CSV file containing image descriptions with columns: image_name, value"
    )
    
    if uploaded_csv:
        st.success(f"✅ CSV uploaded: {uploaded_csv.name}")
        st.info(f"File size: {uploaded_csv.size:,} bytes")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Upload Images section
with col2:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("🖼️ Upload Images")
    st.markdown("*Supported formats: PNG, JPG, JPEG*")
    
    uploaded_images = st.file_uploader(
        "Choose image files",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="images_upload",
        help="Image files named as <number>.jpg matching CSV image_name column"
    )
    
    if uploaded_images:
        st.success(f"✅ Images uploaded: {len(uploaded_images)} files")
        
        # # Show image preview
        # if len(uploaded_images) <= 5:  # Only show preview for small sets
        #     st.markdown("**Preview:**")
        #     cols = st.columns(min(len(uploaded_images), 5))
        #     for i, img in enumerate(uploaded_images[:5]):
        #         with cols[i]:
        #             st.image(img, caption=img.name, width=100)
        # else:
        #     st.info(f"Too many images to preview. Total: {len(uploaded_images)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Processing section
st.markdown("---")

# Process button
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    process_button = st.button(
        "🚀 Start Processing", 
        type="primary", 
        use_container_width=True,
        disabled=not (uploaded_csv and uploaded_images)
    )

# Results section
if process_button:
    if not uploaded_csv or not uploaded_images:
        st.error("❌ Please upload both CSV file and images before processing")
    else:
        # Initialize processor
        processor = RAGProcessor()
        
        # Show processing status
        with st.spinner("🔄 Processing RAG data ingestion..."):
            # Run workflow
            results = processor.run_full_workflow(uploaded_csv, uploaded_images)
        
        st.markdown("---")
        st.subheader("📊 Processing Results")
        
        # Results statistics
        if results['total_records'] > 0:
            st.markdown('<div class="stats-container">', unsafe_allow_html=True)
            
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)

            with col_stat1:
                st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-number">{results['total_records']}</div>
                    <div>Total Records</div>
                </div>
                ''', unsafe_allow_html=True)

            with col_stat2:
                st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-number" style="color: #28a745;">{results['successful']}</div>
                    <div>Successful</div>
                </div>
                ''', unsafe_allow_html=True)

            with col_stat3:
                st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-number" style="color: #ffc107;">{results.get('skipped', 0)}</div>
                    <div>Skipped</div>
                </div>
                ''', unsafe_allow_html=True)

            with col_stat4:
                st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-number" style="color: #dc3545;">{results['failed']}</div>
                    <div>Failed</div>
                </div>
                ''', unsafe_allow_html=True)

            with col_stat5:
                st.markdown(f'''
                <div class="stat-box">
                    <div class="stat-number">{results['processing_time']}s</div>
                    <div>Processing Time</div>
                </div>
                ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Success summary
        processed_count = results['successful'] + results.get('skipped', 0)
        if processed_count > 0:
            st.markdown(f'''
            <div class="result-success">
                <h4>✅ Processing Completed!</h4>
                <p><strong>New records processed:</strong> {results['successful']}/{results['total_records']}</p>
                <p><strong>Skipped (already exist):</strong> {results.get('skipped', 0)}/{results['total_records']}</p>
                <p><strong>S3 Folder:</strong> {results['s3_folder']}</p>
                <p><strong>Processing Time:</strong> {results['processing_time']} seconds</p>
            </div>
            ''', unsafe_allow_html=True)

            # Show successful items
            if results['success_items']:
                with st.expander(f"✅ View New Items ({len(results['success_items'])})"):
                    for item in results['success_items']:
                        st.write(f"• {item}")

        # Show skipped items
        if results.get('skipped_items'):
            st.markdown(f'''
            <div class="result-warning">
                <h4>⏭️ Skipped Items ({len(results['skipped_items'])})</h4>
                <p>These images already exist in the database and were skipped:</p>
            </div>
            ''', unsafe_allow_html=True)

            with st.expander(f"⏭️ View Skipped Items ({len(results['skipped_items'])})"):
                for item in results['skipped_items']:
                    st.write(f"• {item}")
        
        # Errors and warnings
        if results['errors']:
            st.markdown(f'''
            <div class="result-warning">
                <h4>⚠️ Issues Found ({len(results['errors'])})</h4>
                <p>Some items could not be processed. See details below:</p>
            </div>
            ''', unsafe_allow_html=True)
            
            with st.expander(f"⚠️ View Issues ({len(results['errors'])})"):
                for error in results['errors']:
                    st.write(f"• {error}")
        
        # Complete failure case
        if results['successful'] == 0 and results.get('skipped', 0) == 0 and results['total_records'] == 0:
            st.markdown('''
            <div class="result-error">
                <h4>❌ Processing Failed</h4>
                <p>No records could be processed. Please check your files and try again.</p>
            </div>
            ''', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🔧 Configure settings in <code>config.py</code> | 📝 Check console logs for detailed information</p>
</div>
""", unsafe_allow_html=True)