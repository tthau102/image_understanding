import streamlit as st
import logging
import json
import pandas as pd
from data_ops import get_db_connection, get_pending_review_items, generate_presigned_url

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'selected_image' not in st.session_state:
        st.session_state.selected_image = None
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ""
    if 'loading_image' not in st.session_state:
        st.session_state.loading_image = False
    if 'cached_images' not in st.session_state:
        st.session_state.cached_images = {}
    if 'last_selected' not in st.session_state:
        st.session_state.last_selected = None

# Call initialization
init_session_state()

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Planogram Compliance Review",
    page_icon="🔍"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        padding: 20px 0;
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
    
    /* Loading animation */
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .loading-shimmer {
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">🔍 Planogram Compliance Review</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Image Review and Analysis System</p>', unsafe_allow_html=True)

# Load pending review data
try:
    conn = get_db_connection()
    pending_items = get_pending_review_items(conn)
    conn.close()

    if not pending_items:
        st.info("📝 No pending review items found")
        st.stop()

except Exception as e:
    st.error(f"❌ Error loading pending review data: {str(e)}")
    st.stop()

# Display statistics
total_items = len(pending_items)
items_with_comments = len([item for item in pending_items if item.get('review_comment')])
compliance_pass = len([item for item in pending_items if item.get('compliance_assessment')])
compliance_fail = total_items - compliance_pass

# Stats row
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

# Apply search filter
search_term = st.session_state.search_term
if search_term:
    filtered_items = [item for item in pending_items if search_term.lower() in item['image_name'].lower()]
else:
    filtered_items = pending_items

# 3-Column Layout
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
    
    # Update search term if changed
    if new_search != st.session_state.search_term:
        st.session_state.search_term = new_search
        st.rerun()
    
    # Scrollable image list
    with st.container(height=500):
        if filtered_items:
            for item in filtered_items:
                image_name = item['image_name']
                compliance = item['compliance_assessment']
                has_comment = bool(item.get('review_comment'))

                # Check if selected
                is_selected = st.session_state.selected_image == image_name

                # Create status indicators
                compliance_icon = "✅" if compliance else "❌"
                comment_icon = "💬" if has_comment else ""

                if is_selected:
                    st.markdown(f"""
                    <div style="background-color: #2196f3; color: white; padding: 10px 16px;
                                margin: 2px 0; border-radius: 6px; border: 1px solid #ddd;
                                text-align: center; font-size: 16px;">
                        {image_name} {compliance_icon} {comment_icon}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    button_text = f"{image_name} {compliance_icon} {comment_icon}"
                    if st.button(button_text, key=f"btn_{image_name}", use_container_width=True):
                        # Set new selection and trigger loading
                        st.session_state.selected_image = image_name
                        st.session_state.loading_image = True
                        st.rerun()
        else:
            st.info("No items found")

# Column 2: Image Display
with col2:
    st.markdown("#### 🖼️ Image Preview")

    if st.session_state.selected_image:
        # Check for new selection
        is_new_selection = (st.session_state.last_selected != st.session_state.selected_image)
        
        if is_new_selection:
            st.session_state.last_selected = st.session_state.selected_image
            st.session_state.loading_image = True
            # Clear cached image for this selection
            image_cache_key = f"img_{st.session_state.selected_image}"
            if image_cache_key in st.session_state.cached_images:
                del st.session_state.cached_images[image_cache_key]

        # Find selected item data
        selected_item = next((item for item in filtered_items
                            if item['image_name'] == st.session_state.selected_image), None)

        if selected_item:
            st.markdown(f"**📷 {selected_item['image_name']}**")

            # Display timestamp
            if selected_item['timestamp']:
                st.caption(f"📅 {selected_item['timestamp']}")

            # Image loading section
            try:
                image_cache_key = f"img_{selected_item['image_name']}"
                
                if st.session_state.loading_image:
                    # Show loading state
                    st.markdown("""
                    <div style="height: 300px; display: flex; align-items: center; justify-content: center;
                                border: 2px dashed #6c757d; border-radius: 10px;"
                         class="loading-shimmer">
                        <div style="text-align: center;">
                            <div style="font-size: 32px; margin-bottom: 10px;">🔄</div>
                            <p style="color: #6c757d; margin: 0; font-weight: 500;">Loading image...</p>
                            <p style="color: #6c757d; margin: 5px 0 0 0; font-size: 12px; opacity: 0.7;">
                                Generating secure access...
                            </p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Generate URL in background
                    if selected_item['s3_url']:
                        presigned_url = generate_presigned_url(selected_item['s3_url'])
                        st.session_state.cached_images[image_cache_key] = presigned_url
                        st.session_state.loading_image = False
                        st.rerun()
                    else:
                        st.session_state.loading_image = False
                        st.error("❌ No S3 URL available for this image")

                else:
                    # Show actual image
                    if image_cache_key in st.session_state.cached_images:
                        cached_url = st.session_state.cached_images[image_cache_key]
                        
                        try:
                            st.image(cached_url, use_container_width=True, caption="Image from S3")
                            
                            # Optional refresh button
                            if st.button("🔄 Refresh", key=f"refresh_{selected_item['image_name']}", help="Reload image"):
                                if image_cache_key in st.session_state.cached_images:
                                    del st.session_state.cached_images[image_cache_key]
                                st.session_state.loading_image = True
                                st.rerun()
                                
                        except Exception as img_error:
                            st.error(f"❌ Image display error: {str(img_error)}")
                            if image_cache_key in st.session_state.cached_images:
                                del st.session_state.cached_images[image_cache_key]
                    else:
                        st.session_state.loading_image = True
                        st.rerun()

            except Exception as e:
                st.session_state.loading_image = False
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

            # Display review comment if exists
            if selected_item.get('review_comment'):
                st.markdown("#### 💬 Review Comment")
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;
                            margin-bottom: 15px; border-left: 4px solid #007bff;">
                    {selected_item['review_comment']}
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

                    # Display shelves analysis
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

                        # Display as DataFrame table
                        if shelves_data:
                            df_shelves = pd.DataFrame(shelves_data)
                            st.dataframe(df_shelves, use_container_width=True, hide_index=True)

                        # Show raw JSON data in expandable section
                        with st.expander("📄 View Raw JSON Data"):
                            st.json(product_data)
                    else:
                        st.warning("⚠️ No shelves data found in the expected format")
                        with st.expander("📄 Raw Data"):
                            st.json(product_data)

                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
                    with st.expander("📄 Raw Data"):
                        st.text(str(selected_item['product_count']))

                except Exception as e:
                    st.error(f"❌ Error parsing product data: {str(e)}")
                    with st.expander("📄 Raw Data"):
                        st.text(str(selected_item['product_count']))
            else:
                st.warning("⚠️ No product analysis data available")
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
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🔧 Configure settings in <code>config.py</code> | 📝 Check console logs for detailed information</p>
</div>
""", unsafe_allow_html=True)