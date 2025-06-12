import streamlit as st
import logging
import base64
from io import BytesIO
from PIL import Image
from rag_processor import RAGProcessor
from data_ops import get_db_connection, get_review_data, get_pending_review_items

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="RAG Data Management",
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

# Main header
st.markdown('<h1 class="main-header">📊 RAG Data Management</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Data Ingestion and Review System</p>', unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["📊 RAG Data Ingestion", "🔍 Review"])

# Tab 1: RAG Data Ingestion
with tab1:
    st.markdown("### Upload CSV and Images for Processing")

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

# Tab 2: Review
with tab2:
    st.markdown("### Review Pending Items")
    
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
        
        if not pending_items:
            st.info("📝 No pending review items found")
            return
            
    except Exception as e:
        st.error(f"❌ Error loading pending review data: {str(e)}")
        return
    
    # Apply search filter
    search_term = st.session_state.search_term
    if search_term:
        filtered_items = [item for item in pending_items if search_term.lower() in item['image_name'].lower()]
    else:
        filtered_items = pending_items
    
    # Pagination setup
    items_per_page = 20
    total_items = len(filtered_items)
    total_pages = max(1, (total_items - 1) // items_per_page + 1)
    
    # Ensure current page is valid
    if st.session_state.current_page > total_pages:
        st.session_state.current_page = 1
    
    # Calculate pagination
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_items = filtered_items[start_idx:end_idx] if filtered_items else []
    
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
            st.session_state.current_page = 1
            st.rerun()
        
        # Pagination controls
        if total_pages > 1:
            col_prev, col_page, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.button("◀", disabled=st.session_state.current_page <= 1):
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with col_page:
                st.markdown(f"**Page {st.session_state.current_page}/{total_pages}**")
            
            with col_next:
                if st.button("▶", disabled=st.session_state.current_page >= total_pages):
                    st.session_state.current_page += 1
                    st.rerun()
        
        # Image list
        st.markdown("---")
        
        if page_items:
            for item in page_items:
                image_name = item['image_name']
                
                # Check if selected
                is_selected = st.session_state.selected_image == image_name
                
                # Create clickable button with conditional styling
                if is_selected:
                    st.markdown(f"""
                    <div style="background-color: #2196f3; color: white; padding: 8px 12px; 
                                margin: 2px 0; border-radius: 5px; border: 2px solid #1976d2;">
                        <strong>📷 {image_name}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(f"📷 {image_name}", key=f"btn_{image_name}", use_container_width=True):
                        st.session_state.selected_image = image_name
                        st.rerun()
        else:
            st.info("No items found")
        
        # Show current range
        if page_items:
            st.caption(f"Showing {start_idx + 1}-{end_idx} of {total_items}")
    
    # Column 2: Image Display
    with col2:
        st.markdown("#### 🖼️ Image Preview")
        
        if st.session_state.selected_image:
            # Find selected item data
            selected_item = next((item for item in filtered_items 
                                if item['image_name'] == st.session_state.selected_image), None)
            
            if selected_item:
                st.markdown(f"**📷 {selected_item['image_name']}**")
                
                try:
                    # Try to display from S3 URL first
                    if selected_item['s3_url']:
                        st.image(selected_item['s3_url'], width=300, caption="Image from S3")
                    # Fallback to base64
                    elif selected_item['image_base64']:
                        image_data = base64.b64decode(selected_item['image_base64'])
                        image = Image.open(BytesIO(image_data))
                        st.image(image, width=300, caption="Image from Database")
                    else:
                        st.error("❌ No image data available")
                        
                except Exception as e:
                    st.error(f"❌ Cannot display image: {str(e)}")
                    
                    # Try fallback if S3 failed
                    if selected_item['s3_url'] and selected_item['image_base64']:
                        try:
                            st.info("🔄 Trying fallback to database image...")
                            image_data = base64.b64decode(selected_item['image_base64'])
                            image = Image.open(BytesIO(image_data))
                            st.image(image, width=300, caption="Image from Database (Fallback)")
                        except Exception as e2:
                            st.error(f"❌ Fallback also failed: {str(e2)}")
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
    
    # Column 3: JSON Product Count Display
    with col3:
        st.markdown("#### 📊 Product Analysis")
        
        if st.session_state.selected_image:
            # Find selected item data
            selected_item = next((item for item in filtered_items 
                                if item['image_name'] == st.session_state.selected_image), None)
            
            if selected_item and selected_item['product_count']:
                try:
                    # Parse JSON
                    product_data = json.loads(selected_item['product_count'])
                    
                    # Get compliance assessment
                    compliance = selected_item['compliance_assessment']
                    compliance_text = "✅ Pass" if compliance else "❌ Fail"
                    compliance_color = "#28a745" if compliance else "#dc3545"
                    
                    # Display summary
                    if 'refrigerator_analysis' in product_data:
                        analysis = product_data['refrigerator_analysis']
                        total_shelves = analysis.get('number_of_shelves', 0)
                        
                        st.markdown(f"""
                        <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                            <strong>🗄️ Refrigerator Analysis</strong><br>
                            Total Shelves: <strong>{total_shelves}</strong><br>
                            Overall Compliance: <span style="color: {compliance_color}; font-weight: bold;">{compliance_text}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Create shelves table
                        if 'shelves' in analysis and analysis['shelves']:
                            shelves_data = []
                            
                            for shelf in analysis['shelves']:
                                shelves_data.append({
                                    'Shelf': shelf.get('shelf', ''),
                                    'Boncha': shelf.get('boncha', 0),
                                    'Abben': shelf.get('abben', 0), 
                                    'Joco': shelf.get('joco', 0),
                                    'Compliance': compliance_text
                                })
                            
                            # Display as DataFrame table
                            df_shelves = pd.DataFrame(shelves_data)
                            
                            # Style the dataframe
                            def style_compliance(val):
                                color = '#28a745' if '✅' in val else '#dc3545'
                                return f'color: {color}; font-weight: bold'
                            
                            styled_df = df_shelves.style.applymap(
                                style_compliance, subset=['Compliance']
                            )
                            
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)
                            
                            # Calculate total products
                            total_products = sum(
                                shelf.get('boncha', 0) + shelf.get('abben', 0) + shelf.get('joco', 0)
                                for shelf in analysis['shelves']
                            )
                            
                            st.markdown(f"""
                            <div style="margin-top: 15px; font-size: 12px; color: #666;">
                                📈 <strong>Summary:</strong> {total_products} total products detected across {total_shelves} shelves
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ No shelves data found")
                    else:
                        st.warning("⚠️ No refrigerator analysis found")
                        
                        # Show raw JSON as fallback
                        with st.expander("📄 Raw JSON Data"):
                            st.json(product_data)
                            
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
                    
                    # Show raw data
                    with st.expander("📄 Raw Data"):
                        st.text(selected_item['product_count'])
                        
                except Exception as e:
                    st.error(f"❌ Error parsing product data: {str(e)}")
            else:
                st.warning("⚠️ No product analysis data available")
        else:
            st.markdown("""
            <div style="height: 200px; display: flex; align-items: center; justify-content: center; 
                        background-color: #fff3cd; border: 2px dashed #ffc107; border-radius: 10px;">
                <p style="color: #856404; text-align: center;">
                    📊 Select an image to view<br>product analysis
                </p>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🔧 Configure settings in <code>config.py</code> | 📝 Check console logs for detailed information</p>
</div>
""", unsafe_allow_html=True)