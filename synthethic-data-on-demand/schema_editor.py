import streamlit as st
from utils import ai_autofill_table, render_agraph
import json

def render_table_card(table, table_idx, all_tables, show_ai_autofill=False):
    """Render an interactive table card"""
    # Ensure table has required structure
    if not isinstance(table, dict):
        table = {"name": f"table_{table_idx}", "columns": [], "primary_key": [], "foreign_keys": []}
    
    table_name = table.get("name", f"table_{table_idx}")
    columns = table.get("columns", [])
    primary_keys = table.get("primary_key", [])
    foreign_keys = table.get("foreign_keys", [])
    
    # Check if this is a new table (no columns yet)
    is_new_table = len(columns) == 0
    
    with st.container():
        # Table header with actions
        if is_new_table and show_ai_autofill:
            # Special header for new tables with AI autofill
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"### 🆕 **{table_name}** *- New Table*")
            with col2:
                if st.button("🤖 AI Setup", key=f"ai_fill_{table_idx}", help="Auto-generate columns with AI", type="primary"):
                    return "ai_fill"
            with col3:
                if st.button("🗑️ Delete", key=f"delete_table_{table_idx}", help="Delete table"):
                    return "delete"
        else:
            # Standard header for established tables
            col1, col2 = st.columns([4, 1])
            with col1:
                if is_new_table:
                    st.markdown(f"### 🆕 **{table_name}** *- Empty Table*")
                else:
                    st.markdown(f"### 📊 **{table_name}**")
            with col2:
                if st.button("🗑️ Delete", key=f"delete_table_{table_idx}", help="Delete table"):
                    return "delete"
        
        # Quick stats with safe access and visual indicators
        num_cols = len(columns)
        num_pks = len(primary_keys)
        num_fks = len(foreign_keys)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if is_new_table:
                st.metric("Columns", num_cols, help="No columns yet - use AI Setup!")
            else:
                st.metric("Columns", num_cols)
        with col2:
            st.metric("Primary Keys", num_pks)
        with col3:
            st.metric("Foreign Keys", num_fks)
        
        # Expandable editor
        with st.expander(f"✏️ Edit {table_name}", expanded=num_cols <= 3):
            # Table name editor
            new_name = st.text_input(
                "Table Name:",
                value=table_name,
                key=f"table_name_{table_idx}"
            )
            table["name"] = new_name
            
            # Columns section
            st.markdown("#### 📋 Columns")
            
            # Add column button at top
            if st.button(f"➕ Add Column", key=f"add_col_top_{table_idx}"):
                table["columns"].append({
                    "name": f"new_column_{len(table['columns']) + 1}",
                    "type": "VARCHAR(255)",
                    "description": "New column description"
                })
                st.experimental_rerun()
            
            # Column editor
            for col_idx, col in enumerate(table.get("columns", [])):
                # Only fix truly malformed columns, preserve existing data
                if not isinstance(col, dict):
                    col = {"name": f"column_{col_idx}", "type": "VARCHAR(255)", "description": ""}
                    table["columns"][col_idx] = col
                
                # Ensure required keys exist but preserve existing values
                if "name" not in col or not col["name"]:
                    col["name"] = f"column_{col_idx}"
                if "type" not in col or not col["type"]:
                    col["type"] = "VARCHAR(255)"
                if "description" not in col:
                    col["description"] = ""
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 4, 1])
                    
                    with col1:
                        new_name = st.text_input(
                            f"Name",
                            value=col["name"],
                            key=f"col_name_{table_idx}_{col_idx}",
                            label_visibility="collapsed"
                        )
                        col["name"] = new_name
                    
                    with col2:
                        type_options = ["VARCHAR(255)", "INT", "BIGINT", "DATE", "TIMESTAMP", "DECIMAL(10,2)", "BOOLEAN", "TEXT", "JSON"]
                        current_type = col["type"]
                        # Try to find current type in options, default to first option if not found
                        type_index = type_options.index(current_type) if current_type in type_options else 0
                        
                        new_type = st.selectbox(
                            f"Type",
                            type_options,
                            index=type_index,
                            key=f"col_type_{table_idx}_{col_idx}",
                            label_visibility="collapsed"
                        )
                        col["type"] = new_type
                    
                    with col3:
                        new_desc = st.text_input(
                            f"Description",
                            value=col["description"],
                            key=f"col_desc_{table_idx}_{col_idx}",
                            label_visibility="collapsed"
                        )
                        col["description"] = new_desc
                    
                    with col4:
                        if st.button("🗑️", key=f"del_col_{table_idx}_{col_idx}", help="Delete column"):
                            table["columns"].pop(col_idx)
                            st.experimental_rerun()
            
            # Primary Keys
            st.markdown("#### 🔑 Primary Keys")
            available_columns = [col.get("name", f"col_{i}") for i, col in enumerate(columns) if isinstance(col, dict)]
            current_pks = [pk for pk in primary_keys if pk in available_columns]
            new_primary_keys = st.multiselect(
                "Select primary key columns:",
                available_columns,
                default=current_pks,
                key=f"pk_{table_idx}",
                help="Primary keys are required for other tables to reference this table"
            )
            table["primary_key"] = new_primary_keys
            
            # Foreign Keys
            st.markdown("#### 🔗 Foreign Keys")
            
            # Show helpful info and suggestions
            other_tables_with_pks = []
            suggested_relationships = []
            
            for t in all_tables:
                if isinstance(t, dict) and t.get("name") != table_name:
                    t_pks = t.get("primary_key", [])
                    if t_pks:
                        other_tables_with_pks.append(t.get("name"))
                        
                        # Check for potential foreign key columns
                        for col in columns:
                            col_name = col.get("name", "").lower()
                            other_table_name = t.get("name", "").lower()
                            
                            # Look for columns that might reference this table
                            if (f"{other_table_name}_id" == col_name or 
                                f"{other_table_name}id" == col_name or
                                col_name.endswith(f"_{other_table_name}_id")):
                                suggested_relationships.append({
                                    "column": col.get("name"),
                                    "references": f"{t.get('name')}({t_pks[0]})"
                                })
            
            if not other_tables_with_pks:
                st.info("💡 **Tip:** Add primary keys to other tables first to create foreign key relationships")
            elif suggested_relationships:
                st.info(f"🔍 **Suggested relationships detected:** {len(suggested_relationships)} potential foreign keys found based on column names")
            
            fk_list = foreign_keys.copy()  # Work with a copy
            
            for fk_idx, fk in enumerate(fk_list):
                # Ensure FK has required structure
                if not isinstance(fk, dict):
                    fk = {"column": "", "references": ""}
                    fk_list[fk_idx] = fk
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 3, 1])
                    
                    with col1:
                        current_fk_col = fk.get("column", "")
                        if available_columns:
                            fk_col_index = available_columns.index(current_fk_col) if current_fk_col in available_columns else 0
                            new_fk_col = st.selectbox(
                                f"FK Column",
                                available_columns,
                                index=fk_col_index,
                                key=f"fk_col_{table_idx}_{fk_idx}",
                                label_visibility="collapsed"
                            )
                            fk["column"] = new_fk_col
                        else:
                            st.info("No columns available")
                    
                    with col2:
                        # Build reference options
                        ref_options = []
                        for t in all_tables:
                            if isinstance(t, dict) and t.get("name") != table_name:  # Don't reference self
                                t_pks = t.get("primary_key", [])
                                for pk in t_pks:
                                    ref_options.append(f"{t.get('name', 'unknown')}({pk})")
                        
                        if ref_options:
                            current_ref = fk.get("references", "")
                            ref_index = ref_options.index(current_ref) if current_ref in ref_options else 0
                            new_ref = st.selectbox(
                                f"References",
                                ref_options,
                                index=ref_index,
                                key=f"fk_ref_{table_idx}_{fk_idx}",
                                label_visibility="collapsed"
                            )
                            fk["references"] = new_ref
                        else:
                            st.info("No primary keys available in other tables")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_fk_{table_idx}_{fk_idx}", help="Delete FK"):
                            fk_list.pop(fk_idx)
                            table["foreign_keys"] = fk_list  # Update immediately
                            st.experimental_rerun()
            
            # Add FK button with better validation
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                if st.button(f"➕ Add Foreign Key", key=f"add_fk_{table_idx}", use_container_width=True):
                    if available_columns:
                        # Build reference options
                        ref_options = []
                        for t in all_tables:
                            if isinstance(t, dict) and t.get("name") != table_name:
                                t_pks = t.get("primary_key", [])
                                for pk in t_pks:
                                    ref_options.append(f"{t.get('name', 'unknown')}({pk})")
                        
                        if ref_options:
                            # Add new foreign key with first available options
                            new_fk = {
                                "column": available_columns[0],
                                "references": ref_options[0]
                            }
                            fk_list.append(new_fk)
                            table["foreign_keys"] = fk_list  # Update the table immediately
                            st.experimental_rerun()
                        else:
                            st.warning("⚠️ No primary keys found in other tables. Add primary keys to other tables first.")
                    else:
                        st.warning("⚠️ No columns available. Add columns to this table first.")
            
            with col2:
                # Auto-detect relationships button
                if suggested_relationships and st.button("🔍 Auto-detect FKs", key=f"auto_fk_{table_idx}", use_container_width=True, help="Automatically create foreign keys based on column names"):
                    # Add all suggested relationships
                    for suggestion in suggested_relationships:
                        # Check if this FK doesn't already exist
                        exists = any(fk.get("column") == suggestion["column"] and fk.get("references") == suggestion["references"] for fk in fk_list)
                        if not exists:
                            fk_list.append(suggestion)
                    
                    table["foreign_keys"] = fk_list
                    st.experimental_rerun()
            
            with col3:
                # Show FK count
                st.metric("FKs", len(fk_list), help="Current foreign key count")
            
            # Always update the table's foreign keys
            table["foreign_keys"] = fk_list
    
    return None

def run():
    # Enhanced page header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #e65c00 0%, #f9ca24 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">🎨 Interactive Schema Canvas</h2>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">
            Live schema editing with real-time visualization
        </p>
    </div>
    """, unsafe_allow_html=True)

    schema = st.session_state.get("schema")
    if not schema or "tables" not in schema:
        st.error("❌ **No Schema Found**")
        st.markdown("Please generate a schema first using the **Schema Generator**.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔙 Go to Schema Generator", type="primary", use_container_width=True):
                st.session_state["step"] = "schema_generator"
                st.experimental_rerun()
        return

    tables = schema["tables"]
    
    # Layout choice with enhanced description
    st.markdown("### 🎯 **Choose Your Editing Mode**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **🎨 Visual Canvas Mode**
        - Interactive diagram view
        - Quick table selection
        - 🤖 AI Setup for new tables
        - *Best for: Quick AI-powered setup*
        """)
    with col2:
        st.markdown("""
        **📋 Detailed Editor Mode**
        - Complete manual table editing
        - Advanced column configuration
        - Detailed relationship management
        - *Best for: Manual fine-tuning*
        """)
    
    view_mode = st.radio(
        "",
        ["🎨 Visual Canvas Mode", "📋 Detailed Editor Mode"],
        horizontal=True,
        help="Choose between visual editing or detailed form editing"
    )
    
    if view_mode == "🎨 Visual Canvas Mode":
        # Split layout: Interactive diagram + Quick editor
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 🖱️ **Interactive Schema Diagram**")
            st.markdown("*Click on tables to edit them quickly*")
            
            if tables:
                selected_table = render_agraph(schema)
                
                if selected_table:
                    st.session_state["quick_edit_table"] = selected_table
            else:
                st.info("No tables to display")
        
        with col2:
            st.markdown("#### ⚡ **Quick Actions**")
            
            # Add new table
            with st.expander("➕ **Add New Table**", expanded=False):
                new_table_name = st.text_input("Table name:", placeholder="e.g., products, orders")
                if st.button("Create Table", use_container_width=True):
                    if new_table_name and new_table_name not in [t["name"] for t in tables]:
                        tables.append({
                            "name": new_table_name,
                            "columns": [],
                            "primary_key": [],
                            "foreign_keys": []
                        })
                        st.success(f"✅ Created '{new_table_name}'")
                        st.experimental_rerun()
                    else:
                        st.error("Please enter a unique table name")
            
            # Quick edit selected table
            selected_table_name = st.session_state.get("quick_edit_table")
            if selected_table_name:
                selected_table = next((t for t in tables if t["name"] == selected_table_name), None)
                if selected_table:
                    is_selected_new = len(selected_table.get("columns", [])) == 0
                    
                    with st.expander(f"✏️ **Edit {selected_table_name}**", expanded=True):
                        if is_selected_new:
                            st.markdown(f"**🆕 New table: `{selected_table_name}`**")
                            st.info("💡 **Tip:** Use the AI Setup button below for smart column generation!")
                            
                            # AI Setup button for new tables in Visual Canvas Mode
                            if st.button("🤖 **AI Setup**", use_container_width=True, type="primary", key=f"visual_ai_setup_{selected_table_name}"):
                                with st.spinner("🤖 AI is designing table structure based on your schema context..."):
                                    autofilled = ai_autofill_table(schema, selected_table_name)
                                    if autofilled:
                                        # Find and update the table in the tables list
                                        for i, t in enumerate(tables):
                                            if t["name"] == selected_table_name:
                                                tables[i] = autofilled
                                                break
                                        st.success(f"✅ AI has generated columns for '{selected_table_name}' table!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("❌ AI autofill failed. Please add columns manually.")
                        else:
                            st.markdown(f"**Quick edit for `{selected_table_name}` table:**")
                        
                        # Quick add column (always available)
                        col_name = st.text_input("Add column:", placeholder="column_name")
                        col_type = st.selectbox("Type:", ["VARCHAR(255)", "INT", "DATE", "BOOLEAN"])
                        if st.button("Add Column", use_container_width=True):
                            if col_name:
                                selected_table["columns"].append({
                                    "name": col_name,
                                    "type": col_type,
                                    "description": f"Description for {col_name}"
                                })
                                st.experimental_rerun()
                        
                        # Show current columns
                        if selected_table.get("columns"):
                            st.markdown("**Current columns:**")
                            for col in selected_table["columns"]:
                                st.text(f"• {col['name']} ({col['type']})")
                        
                        # Switch to detailed mode for manual editing
                        if not is_selected_new:
                            st.markdown("---")
                            if st.button("📋 **Switch to Detailed Mode for Manual Editing**", use_container_width=True):
                                st.session_state["detailed_mode_table"] = selected_table_name
                                # Auto-switch to detailed mode
                                st.experimental_rerun()
    
    else:
        # Detailed editor mode
        st.markdown("### 📊 **Schema Tables**")
        
        # Check for new tables and show helpful message
        new_tables = [t for t in tables if len(t.get("columns", [])) == 0]
        if new_tables:
            st.info(f"💡 **{len(new_tables)} new table(s) detected!** Switch to **Visual Canvas Mode** for quick AI-powered setup, or manually configure them below.")
        
        # Add new table button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ **Add New Table**", use_container_width=True):
                st.session_state["show_add_table"] = True
        
        # Add table form
        if st.session_state.get("show_add_table", False):
            with st.expander("🆕 **Create New Table**", expanded=True):
                new_table_name = st.text_input("Table name:", placeholder="e.g., customers, orders, products")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Create", type="primary"):
                        if new_table_name and new_table_name not in [t["name"] for t in tables]:
                            tables.append({
                                "name": new_table_name,
                                "columns": [],
                                "primary_key": [],
                                "foreign_keys": []
                            })
                            st.session_state["show_add_table"] = False
                            st.experimental_rerun()
                        else:
                            st.error("Please enter a unique table name")
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state["show_add_table"] = False
                        st.experimental_rerun()
        
        # Render table cards (without AI autofill - this is manual mode)
        for table_idx, table in enumerate(tables):
            action = render_table_card(table, table_idx, tables, show_ai_autofill=False)
            
            if action == "delete":
                tables.pop(table_idx)
                st.experimental_rerun()
    
    # Save changes
    schema["tables"] = tables
    st.session_state["schema"] = schema
    
    # Navigation
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔙 Back to Generator", use_container_width=True):
            st.session_state["step"] = "schema_generator"
            st.experimental_rerun()
    
    with col2:
        if st.button("👁️ Preview Schema", use_container_width=True):
            st.session_state["show_schema_preview"] = not st.session_state.get("show_schema_preview", False)
    
    with col3:
        if st.button("🔄 Reset All Tables", use_container_width=True):
            if st.session_state.get("confirm_reset"):
                schema["tables"] = []
                st.session_state["confirm_reset"] = False
                st.experimental_rerun()
            else:
                st.session_state["confirm_reset"] = True
                st.warning("Click again to confirm reset")
    
    with col4:
        if st.button("🎲 Generate Data", type="primary", use_container_width=True):
            st.session_state["step"] = "data_generator"
            st.experimental_rerun()

    # Schema preview (collapsible)
    if st.session_state.get("show_schema_preview", False):
        st.markdown("### 📄 **Current Schema (JSON)**")
        st.code(json.dumps(schema, indent=2), language="json", line_numbers=True)