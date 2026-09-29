import streamlit as st
import json
from utils import call_gemini_schema, render_er, render_agraph, normalize_schema


def run():
    # Enhanced page header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">🏗️ Step 2: Schema Generation</h2>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">
            AI-generated database schema based on your requirements
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Check if we have an uploaded schema (from JSON upload path)
    uploaded_schema = st.session_state.get("uploaded_schema")
    schema_source = st.session_state.get("schema_source")
    
    # Check if we have AI wizard data (from AI generation path)
    user_intent = st.session_state.get("input_wizard_intent")
    answers = st.session_state.get("input_wizard_answers")

    # Handle uploaded schema path
    if uploaded_schema and schema_source == "uploaded":
        st.success("✅ **Using your uploaded schema**")
        st.info("📄 Schema loaded from your JSON upload - skipping AI generation")
        
        schema = uploaded_schema
        # Store it in the standard session key for consistency
        st.session_state["schema"] = schema
        
    # Handle AI generation path  
    elif user_intent and answers:
        # Only generate schema if not already done for this input/answers
        if (
            "schema" not in st.session_state
            or st.session_state.get("schema_intent") != user_intent
            or st.session_state.get("schema_answers") != answers
        ):
            st.markdown("### 🤖 **Generating Your Schema...**")
            with st.spinner("AI is creating your database schema based on your requirements..."):
                schema = call_gemini_schema(user_intent, answers)
                schema = normalize_schema(schema)
                st.session_state["schema"] = schema
                st.session_state["schema_intent"] = user_intent
                st.session_state["schema_answers"] = answers
            st.success("✅ Schema generated successfully!")
        else:
            schema = st.session_state["schema"]
    
    # No data available - redirect to input wizard
    else:
        st.error("❌ **Prerequisites Missing**")
        st.markdown("Please complete the **Input Wizard** first to define your data requirements.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔙 Go to Input Wizard", type="primary", use_container_width=True):
                st.session_state["step"] = "input_wizard"
                st.experimental_rerun()
        return
        
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
            schema = normalize_schema(schema)
            st.session_state["schema"] = schema  # update session state with parsed dict
        except Exception as e:
            st.error(f"❌ Failed to parse schema JSON: {e}")
            return

    # Schema summary
    if schema and isinstance(schema, dict):
        tables = schema.get("tables", [])
        total_columns = sum(len(table.get("columns", [])) for table in tables)
        
        # Summary cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Tables", len(tables))
        with col2:
            st.metric("🗂️ Total Columns", total_columns)
        with col3:
            st.metric("🔗 Relationships", len(schema.get("relationships", [])))

    # Visualization options
    st.markdown("### 👁️ **Schema Visualization**")
    st.markdown("*Choose how you'd like to view your database schema:*")
    
    viz_mode = st.radio(
        "",
        ["📋 JSON View", "🎨 Static Diagram", "🖱️ Interactive Diagram"],
        horizontal=True,
        key="viz_mode",
        help="Different ways to visualize your database schema"
    )
    
    if viz_mode == "📋 JSON View":
        st.markdown("#### 📄 **Raw Schema Structure**")
        st.code(json.dumps(schema, indent=2), language="json", line_numbers=True)
        
    elif viz_mode == "🎨 Static Diagram":
        st.markdown("#### 🎨 **Entity Relationship Diagram**")
        try:
            dot = render_er(schema)
            st.graphviz_chart(dot)
        except Exception as e:
            st.error(f"❌ Error rendering diagram: {e}")
            
    elif viz_mode == "🖱️ Interactive Diagram":
        st.markdown("#### 🖱️ **Interactive Schema Explorer**")
        st.markdown("*Click on tables to see detailed column information*")
        try:
            selected = render_agraph(schema)
            if selected:
                # selected is the node id (table name)
                table = next((t for t in schema.get("tables", []) if t["name"] == selected), None)
                if table:
                    st.markdown(f"### 📋 **Details for `{table['name']}`**")
                    columns_data = []
                    for col in table.get("columns", []):
                        columns_data.append({
                            "Column": col.get("name", ""),
                            "Type": col.get("type", ""),
                            "Description": col.get("description", ""),
                            "Key": "🔑" if col.get("is_primary_key") else "🔗" if col.get("is_foreign_key") else ""
                        })
                    st.table(columns_data)
        except Exception as e:
            st.error(f"❌ Error rendering interactive diagram: {e}")

    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔙 Back to Wizard", use_container_width=True):
            st.session_state["step"] = "input_wizard"
            st.experimental_rerun()
    
    with col2:
        # Only show regenerate for AI-generated schemas
        if schema_source != "uploaded":
            if st.button("🔄 Regenerate Schema", use_container_width=True):
                # Clear schema to force regeneration
                if "schema" in st.session_state:
                    del st.session_state["schema"]
                st.experimental_rerun()
        else:
            st.info("📄 Uploaded schema - use Edit to modify")
    
    with col3:
        if st.button("✏️ Edit Schema", type="primary", use_container_width=True):
            st.session_state["step"] = "schema_editor" 
            st.experimental_rerun()