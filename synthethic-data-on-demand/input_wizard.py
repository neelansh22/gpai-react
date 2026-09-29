import streamlit as st
import json
from utils import call_llm, extract_questions_from_llm_response

def validate_json_schema(uploaded_schema):
    """
    Validate and format uploaded JSON schema for synthetic data generation
    Expects the exact format that AI models generate
    """
    try:
        # Parse JSON
        schema = json.loads(uploaded_schema)
        
        if not isinstance(schema, dict):
            return False, "Schema must be a JSON object"
        
        # Check for required 'tables' field
        if "tables" not in schema:
            return False, "Schema must contain a 'tables' field"
        
        tables = schema["tables"]
        if not isinstance(tables, list):
            return False, "'tables' must be an array of table objects"
        
        if len(tables) == 0:
            return False, "At least one table must be defined"
        
        # Validate each table structure
        for table_idx, table in enumerate(tables):
            if not isinstance(table, dict):
                return False, f"Table at index {table_idx} must be an object"
            
            # Required fields for each table
            required_table_fields = ["name", "columns", "primary_key", "foreign_keys"]
            for field in required_table_fields:
                if field not in table:
                    return False, f"Table '{table.get('name', f'at index {table_idx}')}' must have a '{field}' field"
            
            table_name = table["name"]
            if not isinstance(table_name, str) or not table_name.strip():
                return False, f"Table name at index {table_idx} must be a non-empty string"
            
            # Validate columns
            columns = table["columns"]
            if not isinstance(columns, list):
                return False, f"'columns' in table '{table_name}' must be an array"
            
            if len(columns) == 0:
                return False, f"Table '{table_name}' must have at least one column"
            
            for col_idx, column in enumerate(columns):
                if not isinstance(column, dict):
                    return False, f"Column at index {col_idx} in table '{table_name}' must be an object"
                
                # Required fields for each column
                required_col_fields = ["name", "type", "description"]
                for field in required_col_fields:
                    if field not in column:
                        return False, f"Column at index {col_idx} in table '{table_name}' must have a '{field}' field"
                
                if not isinstance(column["name"], str) or not column["name"].strip():
                    return False, f"Column name at index {col_idx} in table '{table_name}' must be a non-empty string"
                
                if not isinstance(column["type"], str) or not column["type"].strip():
                    return False, f"Column type for '{column['name']}' in table '{table_name}' must be a non-empty string"
            
            # Validate primary_key
            primary_key = table["primary_key"]
            if not isinstance(primary_key, list):
                return False, f"'primary_key' in table '{table_name}' must be an array"
            
            # Validate foreign_keys
            foreign_keys = table["foreign_keys"]
            if not isinstance(foreign_keys, list):
                return False, f"'foreign_keys' in table '{table_name}' must be an array"
            
            for fk_idx, foreign_key in enumerate(foreign_keys):
                if not isinstance(foreign_key, dict):
                    return False, f"Foreign key at index {fk_idx} in table '{table_name}' must be an object"
                
                required_fk_fields = ["column", "references"]
                for field in required_fk_fields:
                    if field not in foreign_key:
                        return False, f"Foreign key at index {fk_idx} in table '{table_name}' must have a '{field}' field"
        
        return True, "Schema is valid and matches the expected AI-generated format"
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return False, f"Schema validation error: {str(e)}"

def generate_clarifying_questions(user_intent):
    """
    Generate clarifying questions based on user intent
    """
    # Determine the domain from user intent for better LLM prompts
    intent_lower = user_intent.lower()
    
    if any(word in intent_lower for word in ['customer', 'retail', 'sale', 'order', 'purchase', 'commerce']):
        # E-commerce/Retail domain - enhanced prompt for LLM
        prompt = f"""
You are an expert in e-commerce and retail data systems. The user wants to create synthetic data for: "{user_intent}"

Generate exactly 3 intelligent clarifying questions that will help you understand their specific requirements for retail/customer data. Focus on:
- Customer segmentation and behavior patterns
- Transaction complexity and business model
- Geographic and market scope
- Product categories and pricing strategies

Each question should have 3-4 practical multiple choice options that reflect real retail scenarios.

Return as JSON array:
[
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}}
]
"""
    elif any(word in intent_lower for word in ['employee', 'hr', 'staff', 'payroll', 'department']):
        # HR/Employee domain - enhanced prompt for LLM
        prompt = f"""
You are an expert in HR and organizational data systems. The user wants to create synthetic data for: "{user_intent}"

Generate exactly 3 intelligent clarifying questions that will help you understand their specific requirements for employee/HR data. Focus on:
- Employee types and organizational hierarchy
- Performance and compensation structures
- Departmental organization and locations
- Compliance and privacy requirements

Each question should have 3-4 practical multiple choice options that reflect real HR scenarios.

Return as JSON array:
[
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}}
]
"""
    elif any(word in intent_lower for word in ['product', 'inventory', 'catalog', 'item']):
        # Product/Inventory domain - enhanced prompt for LLM
        prompt = f"""
You are an expert in product management and inventory systems. The user wants to create synthetic data for: "{user_intent}"

Generate exactly 3 intelligent clarifying questions that will help you understand their specific requirements for product/inventory data. Focus on:
- Product categorization and attributes
- Supply chain and vendor relationships
- Pricing models and cost structures
- Inventory tracking and variants

Each question should have 3-4 practical multiple choice options that reflect real product management scenarios.

Return as JSON array:
[
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}}
]
"""
    elif any(word in intent_lower for word in ['financial', 'transaction', 'payment', 'banking', 'account']):
        # Financial domain - enhanced prompt for LLM
        prompt = f"""
You are an expert in financial systems and banking data. The user wants to create synthetic data for: "{user_intent}"

Generate exactly 3 intelligent clarifying questions that will help you understand their specific requirements for financial data. Focus on:
- Transaction types and payment methods
- Regulatory compliance and audit requirements
- Customer relationship depth and services
- Risk management and fraud detection

Each question should have 3-4 practical multiple choice options that reflect real financial scenarios.

Return as JSON array:
[
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}}
]
"""
    else:
        # Generic domain - enhanced prompt for LLM
        prompt = f"""
You are a data architecture expert. The user wants to create synthetic data for: "{user_intent}"

Analyze their intent and generate exactly 3 intelligent clarifying questions that will help you understand their specific requirements. Focus on:
- The primary business purpose and use case
- Data complexity and relationship requirements
- Temporal aspects and historical needs
- Integration and analytical requirements

Each question should have 3-4 practical multiple choice options that are relevant to their specific domain.

Return as JSON array:
[
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}},
{{"question": "your contextual question here?", "options": ["option1", "option2", "option3"]}}
]
"""
    
    try:
        response = call_llm(prompt, mode="questions")
        
        if not response or response.strip() == "":
            st.error("❌ No response from LLM - check your API configuration and limits")
            return []
        
        questions = extract_questions_from_llm_response(response)
        
        # Filter to ensure only valid multiple-choice questions
        if isinstance(questions, list):
            valid_questions = []
            for q in questions:
                if isinstance(q, dict) and q.get("options") and len(q.get("options", [])) >= 2:
                    valid_questions.append(q)
            
            if len(valid_questions) >= 3:
                return valid_questions[:3]  # Return exactly 3 valid questions
            elif len(valid_questions) > 0:
                return valid_questions  # Return what we have if less than 3
        
        st.error("❌ LLM did not return valid multiple-choice questions")
        st.error(f"Raw response: {str(response)[:300]}...")
        return []
        
    except Exception as e:
        st.error(f"❌ Error generating questions: {str(e)}")
        return []

def run():
    # Enhanced page header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">📝 Step 1: Define Your Data Intent</h2>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">
            Choose how you want to define your synthetic data structure
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Method selection tabs
    tab1, tab2 = st.tabs(["🤖 AI-Assisted Generation", "📄 Upload JSON Schema"])
    
    with tab1:
        st.markdown("### 💭 **Describe Your Data Requirements**")
        st.markdown("*Let AI generate clarifying questions based on your description*")
        
        # Intent input section
        user_intent = st.text_area(
            "Describe your dataset:",
            placeholder="e.g., 'Customer data for an e-commerce platform selling electronics with order history and product reviews'",
            key="user_intent", 
            value=st.session_state.get("input_wizard_intent", ""),
            height=100,
            help="Provide details about the domain, entities, and relationships you want in your synthetic dataset"
        )

        # Only generate questions if user_intent is new or questions not already stored
        if user_intent:
            if "input_wizard_questions" not in st.session_state or st.session_state.get("input_wizard_intent") != user_intent:
                with st.spinner("🤖 AI is analyzing your request and generating clarifying questions..."):
                    questions = generate_clarifying_questions(user_intent)
                    st.session_state["input_wizard_questions"] = questions
                    st.session_state["input_wizard_intent"] = user_intent
            else:
                questions = st.session_state["input_wizard_questions"]

            if not questions:
                st.error("❌ Failed to generate questions. Please check your LLM configuration and try again.")
                st.info("💡 **Tip**: Try simplifying your data description or check if your LLM server is running correctly.")
                return

            # Questions section with enhanced styling
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 2rem 0;">
                <h3 style="color: #495057; margin-top: 0;">🎯 Clarifying Questions</h3>
                <p style="color: #6c757d; margin-bottom: 1rem;">
                    Please answer these questions to help refine your dataset specifications:
                </p>
            </div>
            """, unsafe_allow_html=True)

            answers = {}
            if isinstance(questions, list) and questions:
                # Check if questions are properly formatted
                valid_questions = []
                for q in questions:
                    if isinstance(q, dict) and "question" in q:
                        valid_questions.append(q)
                    elif isinstance(q, str):
                        # Convert string questions to dict format
                        valid_questions.append({"question": q, "options": []})
                
                if not valid_questions:
                    st.error("❌ Questions are not in the expected format. Please try again.")
                    st.info("💡 **Tip**: Try a simpler description or check your LLM configuration.")
                    return
                    
                for idx, q in enumerate(valid_questions):
                    st.markdown(f"**Question {idx + 1}:**")
                    q_key = f"q_{idx}"
                    options = q.get("options", [])
                    question_text = q.get("question", f"Question {idx + 1}")
                    
                    # Use multiselect for questions with options, text input for open-ended
                    if isinstance(options, list) and options:
                        answers[question_text] = st.multiselect(
                            question_text, 
                            options, 
                            key=q_key,
                            help="You can select multiple options if applicable"
                        )
                    else:
                        answers[question_text] = st.text_input(
                            question_text, 
                            key=q_key,
                            help="Provide a detailed answer to help generate better schema"
                        )
                    st.markdown("---")
                    
                st.session_state["input_wizard_answers"] = answers

                # Enhanced next button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 Generate Schema", type="primary", use_container_width=True):
                        st.session_state["step"] = "schema_generator"
                        st.experimental_rerun()
            else:
                st.error("❌ Failed to parse clarifying questions. Please check your LLM configuration and try again.")
                st.warning("**Debug Info:** Questions format is incorrect")
                
                # Provide fallback manual option
                st.markdown("### 🛠️ **Manual Fallback**")
                st.info("You can still proceed manually. Answer these basic questions:")
                
                fallback_answers = {}
                fallback_answers["Data Volume"] = st.selectbox(
                    "How many records do you need?", 
                    ["100-1,000", "1,000-10,000", "10,000+"], 
                    key="fallback_volume"
                )
                fallback_answers["Time Period"] = st.text_input(
                    "What time period should the data cover?", 
                    key="fallback_period",
                    placeholder="e.g., Last 6 months, Historical data from 2020-2024"
                )
                fallback_answers["Key Entities"] = st.text_input(
                    "What are the main entities in your data?", 
                    key="fallback_entities",
                    placeholder="e.g., Customers, Orders, Products, Reviews"
                )
                
                st.session_state["input_wizard_answers"] = fallback_answers
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 Proceed with Manual Answers", type="primary", use_container_width=True):
                        st.session_state["step"] = "schema_generator"
                        st.experimental_rerun()
    
    with tab2:
        st.markdown("### 📄 **Upload Your JSON Schema**")
        st.markdown("*Already have a schema? Upload it directly and skip the AI generation step*")
        
        # Schema format documentation
        with st.expander("📋 **Expected JSON Schema Format (AI-Generated Compatible)**", expanded=False):
            st.markdown("""
            **This is the exact format our AI models generate. Use this structure for compatibility:**
            
            ```json
            {
              "tables": [
                {
                  "name": "Customers",
                  "columns": [
                    {
                      "name": "id",
                      "type": "INT",
                      "description": "Primary key"
                    },
                    {
                      "name": "first_name",
                      "type": "VARCHAR(255)",
                      "description": "Customer's first name"
                    },
                    {
                      "name": "email",
                      "type": "VARCHAR(255)",
                      "description": "Customer's email address"
                    },
                    {
                      "name": "created_at",
                      "type": "TIMESTAMP",
                      "description": "Creation timestamp"
                    }
                  ],
                  "primary_key": ["id"],
                  "foreign_keys": []
                },
                {
                  "name": "Orders",
                  "columns": [
                    {
                      "name": "id",
                      "type": "INT",
                      "description": "Primary key"
                    },
                    {
                      "name": "customer_id",
                      "type": "INT",
                      "description": "Foreign key to Customers table"
                    },
                    {
                      "name": "total_amount",
                      "type": "DECIMAL(10,2)",
                      "description": "Total amount of the order"
                    },
                    {
                      "name": "order_date",
                      "type": "TIMESTAMP",
                      "description": "Order date"
                    }
                  ],
                  "primary_key": ["id"],
                  "foreign_keys": [
                    {
                      "column": "customer_id",
                      "references": "Customers(id)"
                    }
                  ]
                }
              ]
            }
            ```
            
            **Required Structure:**
            - Root object must have `"tables"` array
            - Each table must have: `"name"`, `"columns"`, `"primary_key"`, `"foreign_keys"`
            - Each column must have: `"name"`, `"type"`, `"description"`
            - `"primary_key"` is an array of column names
            - `"foreign_keys"` is an array of objects with `"column"` and `"references"`
            
            **Supported column types:** `INT`, `VARCHAR(n)`, `TEXT`, `DECIMAL(p,s)`, `TIMESTAMP`, `DATE`, `BOOLEAN`
            """)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a JSON schema file",
            type=['json'],
            key="schema_upload",
            help="Upload a JSON file containing your data schema in the AI-generated format"
        )
        
        # Text area for direct JSON input
        st.markdown("**Or paste your JSON schema directly:**")
        json_input = st.text_area(
            "JSON Schema:",
            placeholder='''{"tables": [{"name": "Users", "columns": [{"name": "id", "type": "INT", "description": "Primary key"}], "primary_key": ["id"], "foreign_keys": []}]}''',
            height=200,
            key="direct_json_input"
        )
        
        # Process uploaded file or direct input
        schema_to_validate = None
        
        if uploaded_file is not None:
            try:
                schema_content = uploaded_file.read().decode('utf-8')
                schema_to_validate = schema_content
                st.success("✅ File uploaded successfully!")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        elif json_input.strip():
            schema_to_validate = json_input.strip()
        
        # Validate and process schema
        if schema_to_validate:
            is_valid, validation_message = validate_json_schema(schema_to_validate)
            
            if is_valid:
                st.success(f"✅ {validation_message}")
                
                # Preview the schema
                try:
                    parsed_schema = json.loads(schema_to_validate)
                    
                    with st.expander("👀 **Schema Preview**", expanded=True):
                        st.markdown("**AI-Generated Schema Format Detected:**")
                        
                        tables = parsed_schema.get("tables", [])
                        for table in tables:
                            table_name = table.get("name", "Unknown")
                            columns = table.get("columns", [])
                            primary_keys = table.get("primary_key", [])
                            foreign_keys = table.get("foreign_keys", [])
                            
                            st.markdown(f"**Table: `{table_name}`**")
                            
                            # Show columns
                            st.markdown("**Columns:**")
                            for column in columns:
                                col_name = column.get("name", "unknown")
                                col_type = column.get("type", "unknown")
                                col_desc = column.get("description", "")
                                is_pk = col_name in primary_keys
                                pk_indicator = " 🔑" if is_pk else ""
                                st.markdown(f"  - `{col_name}`: {col_type}{pk_indicator} - {col_desc}")
                            
                            # Show foreign keys
                            if foreign_keys:
                                st.markdown("**Foreign Keys:**")
                                for fk in foreign_keys:
                                    col = fk.get("column", "unknown")
                                    ref = fk.get("references", "unknown")
                                    st.markdown(f"  - `{col}` → `{ref}`")
                            
                            st.markdown("---")
                    
                    # Store the schema and skip to schema_generator step for seamless integration
                    st.session_state["uploaded_schema"] = parsed_schema
                    st.session_state["schema_source"] = "uploaded"
                    st.session_state["input_wizard_schema"] = parsed_schema  # For schema_generator compatibility
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🚀 Use This Schema", type="primary", use_container_width=True):
                            # Set the step to schema_generator so it can process the uploaded schema
                            st.session_state["step"] = "schema_generator"
                            st.experimental_rerun()
                            
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON format in schema")
            else:
                st.error(f"❌ Schema validation failed: {validation_message}")
                st.info("💡 **Tip**: Check the expected format in the documentation above")

