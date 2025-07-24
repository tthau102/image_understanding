"""
Review tab component for Planogram Compliance application.
"""
import streamlit as st
import json
import pandas as pd
from typing import List, Dict, Optional
from app.services.data_ops import DatabaseService, generate_presigned_url

def render_stats_cards(pending_items: List[Dict]):
    """Render statistics cards with modern design"""
    total_items = len(pending_items)
    items_with_comments = len([item for item in pending_items if item.get('review_comment')])
    compliance_pass = len([item for item in pending_items if item.get('compliance_assessment')])
    compliance_fail = total_items - compliance_pass
    
    # Modern stats cards
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-content">
                <div class="metric-number">{total_items}</div>
                <div class="metric-label">Total Items</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="metric-card success">
            <div class="metric-icon">✅</div>
            <div class="metric-content">
                <div class="metric-number">{compliance_pass}</div>
                <div class="metric-label">Compliance Pass</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="metric-card danger">
            <div class="metric-icon">❌</div>
            <div class="metric-content">
                <div class="metric-number">{compliance_fail}</div>
                <div class="metric-label">Compliance Fail</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="metric-card info">
            <div class="metric-icon">💬</div>
            <div class="metric-content">
                <div class="metric-number">{items_with_comments}</div>
                <div class="metric-label">With Comments</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_image_list(filtered_items: List[Dict]) -> Optional[str]:
    """Render scrollable image list with modern design"""
    st.markdown("#### 📷 Pending Images")
    
    # Search functionality
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_term = st.text_input(
            "",
            value=st.session_state.get('search_term', ''),
            placeholder="🔍 Search images...",
            key="search_input",
            label_visibility="collapsed"
        )
    
    with search_col2:
        if st.button("🔄", help="Refresh", use_container_width=True):
            st.rerun()
    
    # Update search term
    if search_term != st.session_state.get('search_term', ''):
        st.session_state.search_term = search_term
        st.rerun()
    
    st.caption(f"📋 Found: {len(filtered_items)} items")
    
    # Scrollable image list with modern cards
    if filtered_items:
        # Custom CSS for image cards
        st.markdown("""
        <style>
        .image-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border: 1px solid #e9ecef;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .image-card:hover {
            border-color: #0066cc;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 102, 204, 0.15);
        }
        
        .image-card.selected {
            border-color: #0066cc;
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            box-shadow: 0 4px 20px rgba(0, 102, 204, 0.2);
        }
        
        .image-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .image-name {
            font-weight: 600;
            color: #1a1a1a;
            font-size: 14px;
        }
        
        .status-badge {
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-pass {
            background: #d4edda;
            color: #155724;
        }
        
        .status-fail {
            background: #f8d7da;
            color: #721c24;
        }
        
        .image-meta {
            font-size: 12px;
            color: #6c757d;
            display: flex;
            justify-content: space-between;
        }
        </style>
        """, unsafe_allow_html=True)
        
        selected_image = None
        
        for item in filtered_items:
            image_name = item['image_name']
            compliance = item['compliance_assessment']
            timestamp = item.get('timestamp', '')
            
            # Status badge
            status_class = "status-pass" if compliance else "status-fail"
            status_text = "✅ Pass" if compliance else "❌ Fail"
            
            # Check if selected
            is_selected = st.session_state.get('selected_image') == image_name
            card_class = "image-card selected" if is_selected else "image-card"
            
            # Create clickable card using button
            if st.button(
                f"📸 {image_name}",
                key=f"img_btn_{image_name}",
                help=f"View details for {image_name}",
                use_container_width=True
            ):
                st.session_state.selected_image = image_name
                st.rerun()
            
            # Show selection state with custom styling
            if is_selected:
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="image-card-header">
                        <div class="image-name">📸 {image_name}</div>
                        <span class="status-badge {status_class}">{status_text}</span>
                    </div>
                    <div class="image-meta">
                        <span>📅 {timestamp}</span>
                        <span>👁️ Selected</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                selected_image = image_name
        
        return selected_image
    else:
        st.info("🔍 No images found matching your search")
        return None

def render_image_preview(selected_item: Dict):
    """Render image preview with modern design"""
    st.markdown("#### 🖼️ Image Preview")
    
    if selected_item:
        # Image header
        st.markdown(f"""
        <div class="preview-header">
            <h4>📷 {selected_item['image_name']}</h4>
            <span class="timestamp">📅 {selected_item.get('timestamp', 'Unknown')}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Image display with error handling
        try:
            if selected_item['s3_url']:
                presigned_url = generate_presigned_url(selected_item['s3_url'])
                st.image(presigned_url, use_container_width=True, caption="Image from S3 Storage")
            else:
                st.error("❌ No S3 URL available for this image")
        except Exception as e:
            st.error(f"❌ Cannot display image: {str(e)}")
            st.info("💡 Please check S3 access permissions")
    else:
        # Placeholder with modern design
        st.markdown("""
        <div class="preview-placeholder">
            <div class="placeholder-content">
                <div class="placeholder-icon">📷</div>
                <h3>Select an Image</h3>
                <p>Choose an image from the list to view details and analysis results</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_analysis_results(selected_item: Dict):
    """Render analysis results with modern design"""
    st.markdown("#### 📊 Analysis Results")
    
    if selected_item:
        # Compliance status with modern card
        compliance = selected_item['compliance_assessment']
        compliance_text = "✅ Compliant" if compliance else "❌ Non-Compliant"
        compliance_class = "success" if compliance else "danger"
        
        st.markdown(f"""
        <div class="analysis-card {compliance_class}">
            <div class="analysis-header">
                <h4>🎯 Compliance Status</h4>
            </div>
            <div class="compliance-status">
                <span class="status-text">{compliance_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
                    
                    st.markdown(f"""
                    <div class="analysis-card info">
                        <div class="analysis-header">
                            <h4>🗄️ Shelf Analysis</h4>
                            <span class="shelf-count">{len(shelves)} Shelves</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create shelves table with modern styling
                    shelves_data = []
                    for shelf in shelves:
                        shelf_number = shelf.get('shelf_number', 'N/A')
                        drinks = shelf.get('drinks', {})
                        
                        shelves_data.append({
                            'Shelf': f"🗄️ Shelf {shelf_number}",
                            'Joco': drinks.get('joco', 0),
                            'Abben': drinks.get('abben', 0),
                            'Boncha': drinks.get('boncha', 0),
                            'Total': sum(drinks.values())
                        })
                    
                    # Display styled dataframe
                    df_shelves = pd.DataFrame(shelves_data)
                    
                    # Custom CSS for dataframe
                    st.markdown("""
                    <style>
                    .stDataFrame {
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.dataframe(
                        df_shelves, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "Shelf": st.column_config.TextColumn("Shelf", width="medium"),
                            "Joco": st.column_config.NumberColumn("Joco", width="small"),
                            "Abben": st.column_config.NumberColumn("Abben", width="small"),
                            "Boncha": st.column_config.NumberColumn("Boncha", width="small"),
                            "Total": st.column_config.NumberColumn("Total", width="small")
                        }
                    )
                else:
                    st.warning("⚠️ No shelves data found in the expected format")
                    
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format in product data")
            except Exception as e:
                st.error(f"❌ Error parsing product data: {str(e)}")
        else:
            st.info("📊 No product analysis data available")
        
        # Review comment
        if selected_item.get('review_comment'):
            st.markdown("#### 💬 Review Comment")
            st.markdown(f"""
            <div class="comment-card">
                <div class="comment-header">
                    <span class="comment-icon">💬</span>
                    <span class="comment-title">Review Comment</span>
                </div>
                <div class="comment-content">
                    {selected_item['review_comment']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Placeholder for analysis
        st.markdown("""
        <div class="analysis-placeholder">
            <div class="placeholder-content">
                <div class="placeholder-icon">📊</div>
                <h3>Analysis Results</h3>
                <p>Select an image to view compliance status and product analysis</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_review_tab():
    """Main render function for Review tab"""
    # Tab header
    st.markdown("""
    <div class="tab-header">
        <h2>🔍 Review Dashboard</h2>
        <p>Monitor and review planogram compliance analysis results</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Load data
        with st.spinner("🔄 Loading review data..."):
            conn = DatabaseService.get_connection()
            pending_items = DatabaseService.get_pending_review_items(conn)
            conn.close()
        
        if not pending_items:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <h3>No Items to Review</h3>
                <p>All items have been processed or no data is available</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Statistics cards
        render_stats_cards(pending_items)
        
        st.markdown("---")
        
        # Filter items based on search
        search_term = st.session_state.get('search_term', '')
        if search_term:
            filtered_items = [item for item in pending_items 
                            if search_term.lower() in item['image_name'].lower()]
        else:
            filtered_items = pending_items
        
        # Three-column layout with improved proportions
        col1, col2, col3 = st.columns([0.3, 0.35, 0.35])
        
        # Column 1: Image List
        with col1:
            selected_image_name = render_image_list(filtered_items)
        
        # Find selected item
        selected_item = None
        if st.session_state.get('selected_image'):
            selected_item = next(
                (item for item in filtered_items 
                 if item['image_name'] == st.session_state.selected_image), 
                None
            )
        
        # Column 2: Image Preview
        with col2:
            render_image_preview(selected_item)
        
        # Column 3: Analysis Results
        with col3:
            render_analysis_results(selected_item)
        
    except Exception as e:
        st.error(f"❌ Error loading review data: {str(e)}")
        st.info("💡 Please check your database connection and configuration")