import streamlit as st
import pandas as pd
import json
from utils import call_llm
import io

# DISABLE PyGWalker completely - it conflicts with Streamlit architecture
PYGWALKER_AVAILABLE = False
STREAMLIT_PYGWALKER_AVAILABLE = False

# PyGWalker tries to run its own server which conflicts with Streamlit
# Instead, we'll build native Streamlit visualizations that are stable
print("ℹ️ PyGWalker disabled - using native Streamlit visualizations for stability")

print("ℹ️ PyGWalker disabled - using native Streamlit visualizations for stability")

def create_advanced_visualizations(df):
    """
    Create comprehensive data visualizations using only Streamlit native components
    This replaces PyGWalker with stable, integrated visualizations
    """
    
    st.markdown("#### 🎨 **Advanced Data Explorer** (Streamlit Native)")
    st.info("✅ **Stable Visualizations**: Using Streamlit's native charting - no crashes, fully integrated!")
    
    # Get column types
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # Create tabs for different visualization types
    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "📊 **Distributions**", 
        "🔗 **Relationships**", 
        "📈 **Trends**", 
        "🎯 **Custom Explorer**"
    ])
    
    with viz_tab1:
        st.markdown("##### 📊 Distribution Analysis")
        
        if numeric_cols:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔢 Numeric Distributions**")
                selected_numeric = st.selectbox("Select numeric column:", numeric_cols, key="dist_numeric")
                if selected_numeric:
                    # Histogram using Streamlit
                    st.bar_chart(df[selected_numeric].value_counts().head(20))
                    
                    # Statistics
                    stats = df[selected_numeric].describe()
                    st.write("**Statistics:**")
                    st.write(stats)
            
            with col2:
                if len(numeric_cols) >= 2:
                    st.markdown("**📊 Numeric Comparison**")
                    num_col1 = st.selectbox("First column:", numeric_cols, key="comp_num1")
                    num_col2 = st.selectbox("Second column:", [c for c in numeric_cols if c != num_col1], key="comp_num2")
                    
                    if num_col1 and num_col2:
                        # Scatter plot
                        chart_data = df[[num_col1, num_col2]].dropna()
                        if not chart_data.empty:
                            st.scatter_chart(chart_data)
                            
                            # Correlation
                            corr = chart_data[num_col1].corr(chart_data[num_col2])
                            st.metric("Correlation", f"{corr:.3f}")
        
        if categorical_cols:
            st.markdown("**🏷️ Categorical Distributions**")
            selected_cat = st.selectbox("Select categorical column:", categorical_cols, key="dist_cat")
            if selected_cat:
                value_counts = df[selected_cat].value_counts().head(15)
                if not value_counts.empty:
                    st.bar_chart(value_counts)
                    
                    # Show unique values
                    unique_count = df[selected_cat].nunique()
                    st.metric("Unique Values", unique_count)
    
    with viz_tab2:
        st.markdown("##### 🔗 Relationship Analysis")
        
        if len(numeric_cols) >= 2:
            st.markdown("**📈 Correlation Matrix**")
            
            # Select columns for correlation
            selected_cols = st.multiselect(
                "Select columns for correlation analysis:",
                numeric_cols,
                default=numeric_cols[:5] if len(numeric_cols) >= 5 else numeric_cols,
                key="corr_cols"
            )
            
            if len(selected_cols) >= 2:
                corr_matrix = df[selected_cols].corr()
                
                # Display correlation matrix as heatmap-style table (compatible with all pandas versions)
                try:
                    # Try with center parameter first (newer pandas)
                    styled_corr = corr_matrix.style.background_gradient(cmap='RdYlBu_r', center=0)
                except TypeError:
                    # Fallback for older pandas versions without center parameter
                    styled_corr = corr_matrix.style.background_gradient(cmap='RdYlBu_r')
                
                st.dataframe(styled_corr, use_container_width=True)
                
                # Strongest correlations
                st.markdown("**🔥 Strongest Correlations:**")
                corr_pairs = []
                for i in range(len(selected_cols)):
                    for j in range(i+1, len(selected_cols)):
                        corr_val = corr_matrix.iloc[i, j]
                        corr_pairs.append((selected_cols[i], selected_cols[j], abs(corr_val)))
                
                # Sort by absolute correlation
                corr_pairs.sort(key=lambda x: x[2], reverse=True)
                
                for i, (col1, col2, abs_corr) in enumerate(corr_pairs[:5]):
                    actual_corr = corr_matrix.loc[col1, col2]
                    st.write(f"{i+1}. **{col1}** ↔ **{col2}**: {actual_corr:.3f}")
        
        # Cross-tabulation for categorical vs numeric
        if categorical_cols and numeric_cols:
            st.markdown("**🔢 Categorical vs Numeric Analysis**")
            col1, col2 = st.columns(2)
            
            with col1:
                cat_col = st.selectbox("Categorical column:", categorical_cols, key="cross_cat")
            with col2:
                num_col = st.selectbox("Numeric column:", numeric_cols, key="cross_num")
            
            if cat_col and num_col:
                # Group by categorical and show numeric statistics
                grouped = df.groupby(cat_col)[num_col].agg(['mean', 'median', 'std']).reset_index()
                st.dataframe(grouped, use_container_width=True)
                
                # Box plot simulation with bar chart of means
                means = df.groupby(cat_col)[num_col].mean()
                st.bar_chart(means)
    
    with viz_tab3:
        st.markdown("##### 📈 Trend Analysis")
        
        # If we have datetime columns
        if datetime_cols:
            st.markdown("**📅 Time Series Analysis**")
            date_col = st.selectbox("Select date column:", datetime_cols, key="trend_date")
            
            if numeric_cols:
                value_col = st.selectbox("Select value column:", numeric_cols, key="trend_value")
                
                if date_col and value_col:
                    # Time series chart
                    time_data = df[[date_col, value_col]].dropna()
                    if not time_data.empty:
                        time_data = time_data.set_index(date_col)
                        st.line_chart(time_data)
                        
                        # Time-based statistics
                        st.write(f"**Trend Summary for {value_col}:**")
                        st.write(f"• Data points: {len(time_data)}")
                        st.write(f"• Date range: {time_data.index.min()} to {time_data.index.max()}")
                        st.write(f"• Average: {time_data[value_col].mean():.2f}")
        else:
            st.info("📅 No datetime columns found for trend analysis")
        
        # Value evolution (even without explicit dates)
        if numeric_cols:
            st.markdown("**📊 Value Evolution**")
            evo_col = st.selectbox("Select column to track evolution:", numeric_cols, key="evolution")
            
            if evo_col:
                # Show evolution by row index (order in dataset)
                evolution_data = df[evo_col].reset_index()
                st.line_chart(evolution_data.set_index('index'))
    
    with viz_tab4:
        st.markdown("##### 🎯 Custom Data Explorer")
        st.info("🔧 **Build Your Own Charts**: Create custom visualizations by selecting dimensions and metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 Chart Configuration**")
            
            chart_type = st.selectbox(
                "Chart Type:",
                ["📊 Bar Chart", "📈 Line Chart", "🎯 Scatter Plot", "📋 Data Table"],
                key="custom_chart_type"
            )
            
            all_cols = list(df.columns)
            x_axis = st.selectbox("X-Axis:", all_cols, key="custom_x")
            
            if chart_type in ["📈 Line Chart", "🎯 Scatter Plot"]:
                y_axis = st.selectbox("Y-Axis:", [c for c in all_cols if c != x_axis], key="custom_y")
            else:
                y_axis = None
        
        with col2:
            st.markdown("**⚙️ Display Options**")
            
            limit_rows = st.checkbox("Limit data points", value=True, key="custom_limit")
            if limit_rows:
                max_points = st.slider("Max points:", 10, 1000, 100, key="custom_max")
            else:
                max_points = len(df)
            
            sort_data = st.checkbox("Sort data", value=False, key="custom_sort")
            if sort_data:
                sort_ascending = st.radio("Sort order:", ["Ascending", "Descending"], key="custom_sort_order") == "Ascending"
        
        # Generate custom chart
        if x_axis:
            chart_data = df[[x_axis] + ([y_axis] if y_axis else [])].dropna()
            
            if sort_data:
                chart_data = chart_data.sort_values(x_axis, ascending=sort_ascending)
            
            chart_data = chart_data.head(max_points)
            
            if not chart_data.empty:
                if chart_type == "📊 Bar Chart":
                    if chart_data[x_axis].dtype in ['object', 'category']:
                        # For categorical data, show value counts
                        counts = chart_data[x_axis].value_counts().head(20)
                        st.bar_chart(counts)
                    else:
                        # For numeric data, show distribution
                        st.bar_chart(chart_data[x_axis].value_counts().head(20))
                
                elif chart_type == "📈 Line Chart":
                    if y_axis:
                        line_data = chart_data.set_index(x_axis)
                        st.line_chart(line_data)
                    else:
                        st.warning("Line charts require both X and Y axis")
                
                elif chart_type == "🎯 Scatter Plot":
                    if y_axis:
                        st.scatter_chart(chart_data[[x_axis, y_axis]])
                    else:
                        st.warning("Scatter plots require both X and Y axis")
                
                elif chart_type == "📋 Data Table":
                    st.dataframe(chart_data, use_container_width=True)
                
                # Show data summary
                st.markdown("**📊 Data Summary:**")
                st.write(f"• Showing {len(chart_data)} of {len(df)} total rows")
                st.write(f"• X-axis ({x_axis}): {chart_data[x_axis].dtype}")
                if y_axis:
                    st.write(f"• Y-axis ({y_axis}): {chart_data[y_axis].dtype}")

def test_pygwalker_streamlit():
    """Test function - always returns False since PyGWalker is disabled"""
    return False

def apply_business_rules(df, business_rules, schema_context):
    """
    Apply business rules to the consolidated dataset using LLM guidance
    """
    if not business_rules.strip():
        return df, "No business rules specified"
    
    # Use LLM to understand and apply business rules
    prompt = f"""
You are a data transformation expert. Given a dataset and business rules, suggest specific data modifications.

DATASET INFO:
- Rows: {len(df)}
- Columns: {list(df.columns)}
- Sample data (first 3 rows):
{df.head(3).to_string()}

BUSINESS RULES TO APPLY:
{business_rules}

SCHEMA CONTEXT:
{json.dumps(schema_context.get("tables", []), indent=2)}

TASK:
Provide specific Python pandas operations to implement these business rules. Focus on:
1. Data validation and constraint enforcement
2. Relationship consistency checks
3. Business logic implementation
4. Data quality improvements

RESPOND WITH:
1. A summary of what needs to be changed
2. Python code snippets using pandas operations
3. Expected impact on data quality

Format your response as:
SUMMARY: [brief description]
CODE: [pandas operations]
IMPACT: [expected improvements]
"""
    
    try:
        response = call_llm(prompt, mode="business_rules")
        
        # For now, return the analysis without actual code execution
        # In production, you'd want to safely execute vetted transformations
        return df, response
        
    except Exception as e:
        return df, f"Error analyzing business rules: {str(e)}"

def enhance_data_with_ai(df, enhancement_type, context=""):
    """
    Use AI to enhance specific aspects of the data
    """
    prompt = f"""
You are a data enhancement specialist. Given a dataset, suggest improvements for: {enhancement_type}

DATASET SAMPLE:
{df.head(10).to_string()}

DATASET INFO:
- Shape: {df.shape}
- Columns: {list(df.columns)}
- Data types: {df.dtypes.to_dict()}
- Data Summary: {df.describe().to_dict()}

ENHANCEMENT TYPE: {enhancement_type}
CONTEXT: {context}

Please provide specific, actionable suggestions for improving this aspect of the data.
"""
    
    try:
        response = call_llm(prompt, mode="data_enhancement")
        return response
    except Exception as e:
        return f"Error generating enhancement suggestions: {str(e)}"

def run():
    # Enhanced page header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">🔬 Step 5: Augment Data</h2>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">
            Explore your consolidated dataset visually and enhance with intelligent business rules
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Check if consolidated data exists
    if "consolidated_data" not in st.session_state:
        st.error("❌ **No Consolidated Data Found**")
        st.markdown("Please generate and consolidate your data first.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔙 Go to Data Generator", type="primary", use_container_width=True):
                st.session_state["step"] = "data_generator"
                st.experimental_rerun()
        return

    # Safely get consolidated data
    consolidated_data = st.session_state.get("consolidated_data")
    
    # Handle both DataFrame and dict/list cases
    if isinstance(consolidated_data, pd.DataFrame):
        consolidated_df = consolidated_data
    elif isinstance(consolidated_data, (dict, list)):
        try:
            consolidated_df = pd.DataFrame(consolidated_data)
        except Exception as e:
            st.error(f"❌ **Invalid Data Format**: Unable to process consolidated data. Error: {str(e)}")
            return
    else:
        st.error("❌ **Invalid Data Type**: Consolidated data is not in a valid format.")
        return
    
    # Verify DataFrame is not empty
    if consolidated_df.empty:
        st.error("❌ **Empty Dataset**: The consolidated dataset is empty.")
        return

    schema = st.session_state.get("schema", {})

    # Dataset overview
    st.markdown("### 🎯 **Master Dataset Overview**")
    
    try:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📏 Rows", len(consolidated_df))
        with col2:
            st.metric("📋 Columns", len(consolidated_df.columns))
        with col3:
            memory_mb = consolidated_df.memory_usage(deep=True).sum() / (1024 * 1024)
            st.metric("💾 Size", f"{memory_mb:.1f} MB")
        with col4:
            total_cells = len(consolidated_df) * len(consolidated_df.columns)
            missing_cells = consolidated_df.isnull().sum().sum()
            missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0
            st.metric("🕳️ Missing %", f"{missing_pct:.1f}%")
    except Exception as e:
        st.error(f"❌ Error calculating dataset metrics: {str(e)}")
        return

    # Visual exploration section
    st.markdown("### 📊 **Visual Data Exploration**")
    
    # Always show the Quick Charts tab first (safer)
    tab1, tab2 = st.tabs(["📈 **Quick Charts**", "🎨 **Advanced Explorer**"])
    
    with tab1:
        # Quick chart options with error handling
        st.markdown("#### 🎯 **Quick Insights**")
        
        try:
            # Column selection for quick analysis
            numeric_cols = consolidated_df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = consolidated_df.select_dtypes(include=['object']).columns.tolist()
            
            if numeric_cols:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**📊 Numeric Analysis**")
                    selected_numeric = st.selectbox("Select numeric column:", numeric_cols)
                    if selected_numeric:
                        # Create distribution chart
                        try:
                            value_counts = consolidated_df[selected_numeric].value_counts().head(10)
                            st.bar_chart(value_counts)
                        except Exception as e:
                            st.error(f"Error creating chart: {str(e)}")
                
                with col2:
                    if len(numeric_cols) >= 2:
                        st.markdown("**🔗 Correlation Analysis**")
                        x_col = st.selectbox("X-axis:", numeric_cols, key="x_axis")
                        y_col = st.selectbox("Y-axis:", [col for col in numeric_cols if col != x_col], key="y_axis")
                        if x_col and y_col:
                            try:
                                chart_data = consolidated_df[[x_col, y_col]].dropna()
                                if not chart_data.empty:
                                    st.scatter_chart(chart_data)
                                else:
                                    st.info("No data available for selected columns")
                            except Exception as e:
                                st.error(f"Error creating scatter plot: {str(e)}")
            
            if categorical_cols:
                st.markdown("#### 📊 **Categorical Analysis**")
                selected_cat = st.selectbox("Select categorical column:", categorical_cols)
                if selected_cat:
                    try:
                        value_counts = consolidated_df[selected_cat].value_counts().head(10)
                        if not value_counts.empty:
                            st.bar_chart(value_counts)
                        else:
                            st.info("No data available for selected column")
                    except Exception as e:
                        st.error(f"Error creating categorical chart: {str(e)}")
                        
            if not numeric_cols and not categorical_cols:
                st.info("📝 No suitable columns found for quick analysis.")
                
            # Add data preview in Quick Charts tab
            st.markdown("#### 📋 **Data Sample**")
            st.dataframe(consolidated_df.head(20), use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ Error in quick insights: {str(e)}")
            st.markdown("**📋 Basic Data Preview:**")
            st.dataframe(consolidated_df.head(10), use_container_width=True)
    
    with tab2:
        # Advanced Explorer with Native Streamlit Visualizations (PyGWalker replacement)
        st.success("✅ **Advanced Explorer**: Powered by native Streamlit components - stable and fully integrated!")
        
        # Create our comprehensive visualization system
        create_advanced_visualizations(consolidated_df)

    # Business rules section
    st.markdown("---")
    st.markdown("### 🎯 **Business Rules Enhancement**")
    
    st.info("💡 **Insight-Driven Rules**: Based on your visual exploration, define business rules to make your data more realistic and business-compliant.")
    
    # Business rules input
    business_rules = st.text_area(
        "**Define Business Rules:**",
        placeholder="""Examples:
• Customer age should be between 18-80 years
• Order date must be after customer registration date  
• High-value customers (>$10K orders) should have premium status
• Product prices should follow realistic market ranges
• Geographic data should be consistent (state/city combinations)
• Referential integrity: all foreign keys must exist in parent tables""",
        height=150,
        help="Describe the business logic and constraints your data should follow"
    )
    
    # AI-powered enhancement options
    st.markdown("#### 🤖 **AI-Powered Enhancements**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧠 Improve Data Quality", use_container_width=True):
            with st.spinner("🔍 Analyzing data quality..."):
                suggestions = enhance_data_with_ai(consolidated_df, "data quality", "Focus on missing values, outliers, and inconsistencies")
                st.markdown("**🎯 AI Suggestions for Data Quality:**")
                st.markdown(suggestions)
    
    with col2:
        if st.button("🔗 Enhance Relationships", use_container_width=True):
            with st.spinner("🔍 Analyzing relationships..."):
                suggestions = enhance_data_with_ai(consolidated_df, "relationships", "Focus on foreign key consistency and referential integrity")
                st.markdown("**🎯 AI Suggestions for Relationships:**")
                st.markdown(suggestions)
    
    with col3:
        if st.button("📊 Realistic Patterns", use_container_width=True):
            with st.spinner("🔍 Analyzing data patterns..."):
                suggestions = enhance_data_with_ai(consolidated_df, "realistic patterns", "Focus on business-realistic distributions and correlations")
                st.markdown("**🎯 AI Suggestions for Realism:**")
                st.markdown(suggestions)

    # Apply business rules
    if business_rules.strip():
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Apply Business Rules", type="primary", use_container_width=True):
                with st.spinner("🤖 Analyzing and applying business rules..."):
                    try:
                        enhanced_df, analysis = apply_business_rules(consolidated_df, business_rules, schema)
                        
                        # Store the enhanced data
                        st.session_state["augmented_data"] = enhanced_df
                        
                        # Show analysis
                        st.success("✅ Business rules analysis completed!")
                        st.markdown("### 🧠 **AI Analysis & Recommendations**")
                        st.markdown(analysis)
                        
                        # Data comparison
                        if not enhanced_df.equals(consolidated_df):
                            st.markdown("### 📊 **Before vs After Comparison**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Original Data (sample):**")
                                st.dataframe(consolidated_df.head(5))
                            with col2:
                                st.markdown("**Enhanced Data (sample):**")
                                st.dataframe(enhanced_df.head(5))
                        
                    except Exception as e:
                        st.error(f"❌ Error applying business rules: {str(e)}")

    # Export enhanced data
    if "augmented_data" in st.session_state:
        st.markdown("---")
        st.markdown("### 📤 **Export Enhanced Dataset**")
        
        augmented_df = st.session_state["augmented_data"]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            csv_data = augmented_df.to_csv(index=False)
            st.download_button(
                label="📁 Download CSV",
                data=csv_data,
                file_name="augmented_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            json_data = augmented_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📁 Download JSON",
                data=json_data,
                file_name="augmented_data.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            # Excel export for enhanced data
            excel_output = io.BytesIO()
            try:
                with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
                    augmented_df.to_excel(writer, sheet_name='Augmented_Data', index=False)
                    # Add a summary sheet
                    summary_data = {
                        'Metric': ['Total Rows', 'Total Columns', 'Missing Values', 'Data Size (MB)'],
                        'Value': [
                            len(augmented_df),
                            len(augmented_df.columns),
                            augmented_df.isnull().sum().sum(),
                            round(augmented_df.memory_usage(deep=True).sum() / (1024*1024), 2)
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                excel_output.seek(0)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_output.getvalue(),
                    file_name="augmented_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error("Excel export failed. Please use CSV instead.")
        
        with col4:
            # Parquet export for large datasets
            parquet_output = io.BytesIO()
            try:
                augmented_df.to_parquet(parquet_output, index=False)
                parquet_output.seek(0)
                st.download_button(
                    label="⚡ Download Parquet",
                    data=parquet_output.getvalue(),
                    file_name="augmented_data.parquet",
                    mime="application/octet-stream",
                    use_container_width=True
                )
            except Exception as e:
                st.button("⚡ Parquet (Unavailable)", disabled=True, use_container_width=True)

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔙 Back to Generator", use_container_width=True):
            st.session_state["step"] = "data_generator"
            st.experimental_rerun()
    
    with col2:
        if st.button("🎨 View Schema", use_container_width=True):
            st.session_state["step"] = "schema_generator"
            st.experimental_rerun()
    
    with col3:
        if st.button("📝 New Project", use_container_width=True):
            # Clear all session state
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
