import streamlit as st
import input_wizard, schema_generator, schema_editor, data_generator, augment_data
from utils import test_local_llm_connection

def is_dataframe_valid(data):
    """Helper function to safely check if data is a valid non-empty DataFrame"""
    try:
        if data is None:
            return False
        # Check if it's a DataFrame-like object with an empty attribute
        if hasattr(data, 'empty'):
            return not data.empty
        # If it's a dict or list, check if it has content
        elif isinstance(data, (dict, list)):
            return len(data) > 0
        # For other objects, check if they're truthy
        else:
            return bool(data)
    except Exception:
        return False

# Enhanced page configuration with custom styling
st.set_page_config(
    page_title="SDoD - Synthetic Data on Demand",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Custom color scheme and styling */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .step-indicator {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
        gap: 1rem;
    }
    
    .step {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        background: #f0f2f6;
        color: #333;
        font-weight: 500;
        min-width: 120px;
        text-align: center;
    }
    
    .step.active {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .step.completed {
        background: #28a745;
        color: white;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Enhanced button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Schema visualization enhancements */
    .schema-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    /* Progress indicator */
    .progress-bar {
        height: 4px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 2px;
        margin: 1rem 0;
    }
    
    /* Enhanced metrics */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def get_step_indicator():
    """Generate step indicator with progress"""
    current_step = st.session_state.get("step", "input_wizard")
    
    steps = [
        ("input_wizard", "📝 Define Intent"),
        ("schema_generator", "🏗️ Build Schema"),
        ("schema_editor", "✏️ Edit Schema"),
        ("data_generator", "🎲 Generate Data"),
        ("augment_data", "🔬 Augment Data")
    ]
    
    completed_steps = []
    if st.session_state.get("input_wizard_answers"):
        completed_steps.append("input_wizard")
    if st.session_state.get("schema"):
        completed_steps.append("schema_generator")
    
    # Handle DataFrames properly to avoid boolean evaluation errors
    generated_data = st.session_state.get("generated_data")
    if is_dataframe_valid(generated_data):
        completed_steps.append("data_generator")
    
    # Fix DataFrame boolean evaluation
    consolidated_data = st.session_state.get("consolidated_data")
    if is_dataframe_valid(consolidated_data):
        completed_steps.append("data_generator")
    
    augmented_data = st.session_state.get("augmented_data")
    if is_dataframe_valid(augmented_data):
        completed_steps.append("augment_data")
    
    step_html = '<div class="step-indicator">'
    for step_id, step_name in steps:
        if step_id == current_step:
            step_html += f'<div class="step active">{step_name}</div>'
        elif step_id in completed_steps:
            step_html += f'<div class="step completed">{step_name}</div>'
        else:
            step_html += f'<div class="step">{step_name}</div>'
    step_html += '</div>'
    
    return step_html

def main():
    # Error recovery mechanism for DataFrame boolean evaluation issues
    try:
        # Validate session state data to prevent DataFrame boolean errors
        for key in ["generated_data", "consolidated_data", "augmented_data"]:
            data = st.session_state.get(key)
            if data is not None:
                try:
                    # Test if this data causes boolean evaluation issues
                    test_bool = bool(data) if not hasattr(data, 'empty') else not data.empty
                except ValueError as e:
                    if "ambiguous" in str(e).lower():
                        st.warning(f"⚠️ Fixing data format issue for {key}")
                        # Don't delete, just skip boolean evaluation for now
                        pass
                except Exception:
                    pass
    except Exception:
        pass  # Silent recovery
    
    # Main header with branding
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Synthetic Data on Demand</h1>
        <p>Define. Configure. Generate.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Step indicator
    st.markdown(get_step_indicator(), unsafe_allow_html=True)
    
    # Enhanced sidebar
    with st.sidebar:
        # Logo section
        st.image("assets/img/NWorks-logo.png", width=280)
        st.markdown("""
        <div style="text-align: center; padding: 0.5rem 0;">
            <p style="color: #667eea; margin: 0; font-size: 1.1rem; font-weight: 500;">Synthetic Data Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        # LLM Configuration section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 🔧 **LLM Configuration**")
        
        llm_source = st.selectbox(
            "Choose AI Backend",
            ["Google Gemini", "Local LLM"],
            key="llm_source",
            help="Select your preferred language model"
        )

        if llm_source == "Google Gemini":
            st.session_state["google_api_key"] = st.text_input(
                "🔑 Google Gemini API Key",
                value=st.session_state.get("google_api_key", ""),
                type="password",
                help="Enter your Google Gemini API key"
            )
        elif llm_source == "Local LLM":
            col1, col2 = st.columns(2)
            with col1:
                st.session_state["local_llm_address"] = st.text_input(
                    "🌐 Address",
                    value=st.session_state.get("local_llm_address", "192.168.1.16"),
                    help="LLM server address"
                )
            with col2:
                st.session_state["local_llm_port"] = st.text_input(
                    "🔌 Port",
                    value=st.session_state.get("local_llm_port", "1234"),
                    help="LLM server port"
                )
            
            # Connection test button
            if st.button("🔍 Test Connection", help="Test connectivity to your Local LLM server"):
                address = st.session_state.get("local_llm_address", "192.168.1.16")
                port = st.session_state.get("local_llm_port", "1234")
                test_local_llm_connection(address, port)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 🧭 **Navigation**")
        
        # Navigation buttons with icons
        if st.button("📝 Input Wizard", use_container_width=True):
            st.session_state["step"] = "input_wizard"
            st.experimental_rerun()
            
        if st.button("🏗️ Schema Generator", use_container_width=True):
            st.session_state["step"] = "schema_generator"
            st.experimental_rerun()
            
        if st.button("✏️ Schema Editor", use_container_width=True):
            st.session_state["step"] = "schema_editor"
            st.experimental_rerun()
            
        if st.button("🎲 Data Generator", use_container_width=True):
            st.session_state["step"] = "data_generator"
            st.experimental_rerun()
            
        if st.button("🔬 Augment Data", use_container_width=True):
            st.session_state["step"] = "augment_data"
            st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Project status section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 📊 **Project Status**")
        
        # Status indicators - handle DataFrames properly using helper function
        intent_status = "✅" if st.session_state.get("input_wizard_answers") else "⏳"
        schema_status = "✅" if st.session_state.get("schema") else "⏳"
        data_status = "✅" if is_dataframe_valid(st.session_state.get("generated_data")) else "⏳"
        consolidated_status = "✅" if is_dataframe_valid(st.session_state.get("consolidated_data")) else "⏳"
        augmented_status = "✅" if is_dataframe_valid(st.session_state.get("augmented_data")) else "⏳"
        
        st.markdown(f"""
        - {intent_status} Intent Defined
        - {schema_status} Schema Created
        - {data_status} Data Generated
        - {consolidated_status} Data Consolidated
        - {augmented_status} Data Augmented
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Clear all section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        
        # Emergency recovery for DataFrame issues
        if st.button("🔧 Fix Data Issues", type="secondary", use_container_width=True, help="Use this if the app is stuck due to data format issues"):
            try:
                # Clear only the problematic DataFrame keys
                for key in ["generated_data", "consolidated_data", "augmented_data"]:
                    if key in st.session_state:
                        data = st.session_state[key]
                        try:
                            # Test if this data causes issues
                            bool(data)
                        except ValueError:
                            st.warning(f"🔧 Removing problematic data: {key}")
                            del st.session_state[key]
                st.success("✅ Data issues resolved! You can continue from where you left off.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Recovery failed: {e}")
        
        if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
            for key in [
                "input_wizard_intent",
                "input_wizard_questions", 
                "input_wizard_answers",
                "schema",
                "schema_intent",
                "schema_answers",
                "generated_data",
                "consolidated_data",
                "augmented_data",
                "step"
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if "step" not in st.session_state:
        st.session_state["step"] = "input_wizard"
    if st.session_state["step"] == "input_wizard":
        input_wizard.run()
    elif st.session_state["step"] == "schema_generator":
        schema_generator.run()
    elif st.session_state["step"] == "schema_editor":
        schema_editor.run()
    elif st.session_state["step"] == "data_generator":
        data_generator.run()
    elif st.session_state["step"] == "augment_data":
        augment_data.run()

if __name__ == "__main__":
    main()