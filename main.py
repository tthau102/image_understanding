"""
Planogram Compliance - Main Streamlit Application
Modern UI with componentized architecture
"""
import streamlit as st
import logging
from pathlib import Path

# Import application components
from app.config import config
from app.components.review_tab import render_review_tab
from app.components.import_tab import render_import_tab

# Setup logging
logger = logging.getLogger(__name__)

def load_custom_css():
    """Load custom CSS for modern styling"""
    try:
        css_file = Path("assets/styles.css")
        if css_file.exists():
            with open(css_file) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            logger.warning("CSS file not found, using embedded styles")
            # Fallback embedded CSS for critical styles
            st.markdown("""
            <style>
            .main-header {
                text-align: center;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 32px;
                border-radius: 16px;
                margin-bottom: 24px;
                border: 1px solid #dee2e6;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .main-header h1 {
                margin: 0 0 8px 0;
                font-size: 2.5rem;
                background: linear-gradient(135deg, #0066cc, #33b5e5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 700;
            }
            
            .main-header p {
                margin: 0;
                color: #6c757d;
                font-size: 1.2rem;
            }
            
            .footer-modern {
                text-align: center;
                color: #6c757d;
                padding: 32px 20px;
                margin-top: 40px;
                border-top: 1px solid #dee2e6;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-radius: 16px;
            }
            
            .footer-modern code {
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', 'Consolas', monospace;
            }
            
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background: #f8f9fa;
                border-radius: 12px;
                padding: 6px;
                border: 1px solid #dee2e6;
            }
            
            .stTabs [data-baseweb="tab"] {
                border-radius: 8px;
                color: #6c757d;
                font-weight: 600;
                padding: 16px 28px;
                border: none;
                background: transparent;
                transition: all 0.3s ease;
                font-size: 1rem;
            }
            
            .stTabs [aria-selected="true"] {
                background: #ffffff;
                color: #0066cc;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transform: translateY(-1px);
            }
            </style>
            """, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error loading CSS: {str(e)}")

def init_session_state():
    """Initialize session state variables"""
    session_vars = {
        'selected_project': None,
        'ls_projects': None,
        'ls_error': None,
        'selected_image': None,
        'search_term': ""
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

def render_header():
    """Render modern application header"""
    st.markdown("""
    <div class="main-header">
        <h1>📊 Planogram Compliance</h1>
        <p>Professional Review System & Label Studio Integration</p>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    """Render modern application footer"""
    # System status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        db_status = "🟢 Connected" if config.DB_CONFIG.get('password') else "🔴 Not Configured"
        st.markdown(f"**Database:** {db_status}")
    
    with col2:
        s3_status = "🟢 Configured" if config.S3_BUCKET_NAME else "🔴 Not Configured"
        st.markdown(f"**S3 Storage:** {s3_status}")
    
    with col3:
        ls_status = "🟢 Configured" if config.LABEL_STUDIO_API_TOKEN else "🔴 Not Configured"
        st.markdown(f"**Label Studio:** {ls_status}")
    
    # Footer info
    st.markdown(f"""
    <div class="footer-modern">
        <p>
            <strong>🔧 {config.APP_NAME}</strong> v{config.APP_VERSION} |
            📝 Configure in <code>.env</code> file |
            🐛 Debug: {'ON' if config.DEBUG else 'OFF'} |
            📊 Log Level: {config.LOG_LEVEL}
        </p>
        <p style="margin-top: 12px; font-size: 0.9rem;">
            Built with ❤️ using Streamlit • Professional planogram compliance analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

def check_configuration():
    """Check and display configuration status"""
    config_errors = config.validate_config()
    
    if config_errors:
        st.error("⚠️ **Configuration Issues Detected**")
        
        with st.expander("🔧 Configuration Details", expanded=True):
            st.markdown("**Missing or invalid configuration:**")
            for error in config_errors:
                st.write(f"• {error}")
            
            st.markdown("**📝 To fix these issues:**")
            st.markdown("""
            1. Copy `.env.example` to `.env`
            2. Edit `.env` with your actual values
            3. Restart the application
            """)
            
            st.code("""
# Example .env configuration
DB_PASSWORD=your-actual-password
S3_BUCKET_NAME=your-s3-bucket
LABEL_STUDIO_API_TOKEN=your-api-token
LAMBDA_FUNCTION_NAME=your-lambda-function
            """)
        
        return False
    
    return True

def main():
    """Main application function with modern architecture"""
    # Page configuration
    st.set_page_config(
        layout="wide",
        page_title="Planogram Compliance",
        page_icon="📊",
        initial_sidebar_state="collapsed",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': f"Planogram Compliance v{config.APP_VERSION}"
        }
    )
    
    # Load custom styling
    load_custom_css()
    
    # Initialize session state
    init_session_state()
    
    # Render header
    render_header()
    
    # Configuration check
    if not check_configuration():
        st.stop()
    
    # Create main tabs with modern styling
    tab1, tab2 = st.tabs(["🔍 Review Dashboard", "📥 Import & Processing"])
    
    # Render tab content using components
    try:
        with tab1:
            render_review_tab()
        
        with tab2:
            render_import_tab()
            
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        
        if config.DEBUG:
            st.exception(e)
        else:
            st.info("💡 Enable debug mode in configuration for detailed error information")
        
        logger.error(f"Application error: {str(e)}", exc_info=True)
    
    # Render footer
    st.markdown("---")
    render_footer()

if __name__ == "__main__":
    main()