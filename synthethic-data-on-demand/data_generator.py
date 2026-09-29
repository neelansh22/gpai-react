import streamlit as st
import pandas as pd
import json
import random
import re
import time
from datetime import datetime, timedelta
from utils import call_llm
import io

def consolidate_data(generated_data, schema):
    """
    Consolidate multiple tables into a single master dataset using foreign key relationships
    """
    if not generated_data or not schema:
        return pd.DataFrame()
    
    tables = schema.get("tables", [])
    relationships = schema.get("relationships", [])
    
    # Start with the main/largest table or first table
    main_table_name = None
    main_table_data = None
    max_rows = 0
    
    # Find the table with most rows (likely the main fact table)
    for table_name, table_data in generated_data.items():
        if table_data and len(table_data) > max_rows:
            max_rows = len(table_data)
            main_table_name = table_name
            main_table_data = table_data
    
    if not main_table_data:
        return pd.DataFrame()
    
    # Convert to DataFrame and keep original column names for main table
    consolidated_df = pd.DataFrame(main_table_data)
    
    # Join other tables based on relationships
    for table_name, table_data in generated_data.items():
        if table_name == main_table_name or not table_data:
            continue
            
        table_df = pd.DataFrame(table_data)
        
        # Find relationship between main table and this table
        relationship_found = False
        for rel in relationships:
            if (rel.get("from_table") == main_table_name and rel.get("to_table") == table_name) or \
               (rel.get("from_table") == table_name and rel.get("to_table") == main_table_name):
                
                # Determine join columns
                if rel.get("from_table") == main_table_name:
                    left_col = rel.get('from_column')
                    right_col = rel.get('to_column')
                else:
                    left_col = rel.get('to_column')
                    right_col = rel.get('from_column')
                
                # Rename columns to avoid conflicts (except join columns)
                table_df_renamed = table_df.copy()
                for col in table_df.columns:
                    if col != right_col:  # Don't rename the join column
                        table_df_renamed = table_df_renamed.rename(columns={col: f"{table_name}_{col}"})
                
                # Perform left join with better null handling
                if left_col in consolidated_df.columns and right_col in table_df.columns:
                    # Check if there are actually matching values before joining
                    main_values = set(consolidated_df[left_col].dropna().astype(str))
                    table_values = set(table_df[right_col].dropna().astype(str))
                    
                    if main_values & table_values:  # If there are common values
                        consolidated_df = consolidated_df.merge(
                            table_df_renamed, 
                            left_on=left_col, 
                            right_on=right_col, 
                            how='left',
                            suffixes=('', f'_{table_name}')
                        )
                        relationship_found = True
                        print(f"✅ Successfully joined {table_name} via {left_col}->{right_col}")
                    else:
                        print(f"⚠️ No matching values for join {table_name}.{right_col} -> {main_table_name}.{left_col}")
                    break
        
        # If no relationship found, try to find common column names (like ID fields)
        if not relationship_found:
            # Look for common patterns like "id", "customer_id", etc.
            main_cols = list(consolidated_df.columns)
            table_cols = list(table_df.columns)
            
            matching_col_pairs = []
            for main_col in main_cols:
                for table_col in table_cols:
                    # Check for exact matches or ID patterns
                    if (main_col == table_col) or \
                       (main_col.endswith('_id') and table_col == 'id') or \
                       (main_col == 'id' and table_col == f"{table_name.lower()}_id") or \
                       (main_col.lower() == f"{table_name.lower()}_id" and table_col == 'id'):
                        matching_col_pairs.append((main_col, table_col))
                        break
            
            # Use the first matching pair found
            if matching_col_pairs:
                main_col, table_col = matching_col_pairs[0]
                
                # Check if there are matching values before joining
                main_values = set(consolidated_df[main_col].dropna().astype(str))
                table_values = set(table_df[table_col].dropna().astype(str))
                
                if main_values & table_values:  # If there are common values
                    # Rename columns to avoid conflicts (except join column)
                    table_df_renamed = table_df.copy()
                    for col in table_df.columns:
                        if col != table_col:  # Don't rename the join column
                            table_df_renamed = table_df_renamed.rename(columns={col: f"{table_name}_{col}"})
                    
                    # Perform left join
                    consolidated_df = consolidated_df.merge(
                        table_df_renamed, 
                        left_on=main_col, 
                        right_on=table_col, 
                        how='left',
                        suffixes=('', f'_{table_name}')
                    )
                    print(f"✅ Successfully joined {table_name} via pattern matching {main_col}->{table_col}")
                else:
                    print(f"⚠️ No matching values for pattern join {table_name}.{table_col} -> main.{main_col}")
                    print(f"    Main values sample: {list(main_values)[:5]}")
                    print(f"    Table values sample: {list(table_values)[:5]}")
    
    # Report consolidation results
    print(f"\n📊 Consolidation Summary:")
    print(f"   Final dataset: {consolidated_df.shape[0]} rows, {consolidated_df.shape[1]} columns")
    
    # Check for columns with all null values
    null_columns = consolidated_df.columns[consolidated_df.isnull().all()].tolist()
    if null_columns:
        print(f"⚠️  Columns with all null values: {null_columns}")
        # Optionally drop completely empty columns
        consolidated_df = consolidated_df.drop(columns=null_columns)
        print(f"   After dropping empty columns: {consolidated_df.shape[1]} columns")
    
    return consolidated_df

def get_adaptive_timeout(attempt, base_timeout=300):
    """
    Get adaptive timeout that increases with each attempt for local LLM
    """
    # Progressive timeouts: 5min, 10min, 15min
    timeouts = [base_timeout, base_timeout * 2, base_timeout * 3]
    return timeouts[min(attempt, len(timeouts) - 1)]

def generate_smart_column_values(column_info, table_name, schema_context, num_rows=100, user_timeout_minutes=15):
    """
    Use LLM to generate realistic column values based on context with adaptive timeouts
    """
    col_name = column_info.get("name", "")
    col_type = column_info.get("type", "VARCHAR(255)")
    col_desc = column_info.get("description", "")
    
    # Circuit breaker: if we've seen too many failures recently, skip AI generation
    if not hasattr(generate_smart_column_values, 'failure_count'):
        generate_smart_column_values.failure_count = 0
        generate_smart_column_values.consecutive_failures = 0
    
    # If we have too many consecutive failures, skip AI and go straight to fallback
    if generate_smart_column_values.consecutive_failures >= 3:
        print(f"🔌 Circuit breaker activated: skipping AI generation for {col_name} (too many consecutive failures)")
        return generate_fallback_values(column_info, table_name, num_rows)
    
    # Build minimal context for the LLM (avoid huge prompts)
    prompt = f"""Generate {num_rows} realistic values for a database column.

Column: {col_name} ({col_type})
Table: {table_name}
Description: {col_desc}

Return ONLY a JSON array of {num_rows} values matching the data type.

Examples:
- For VARCHAR/TEXT: ["Value 1", "Value 2", ...]  
- For INT: [1, 2, 3, ...]
- For DATE: ["2023-01-15", "2023-03-22", ...]
- For BOOLEAN: [true, false, true, ...]

Generate realistic, diverse values."""
    
    max_retries = 3  # Increased retries with adaptive timeouts
    
    # Add overall timeout protection for the entire function based on user preference
    import time
    start_time = time.time()
    max_function_time = user_timeout_minutes * 60  # Convert to seconds
    
    for attempt in range(max_retries):
        # Check if we've exceeded the overall time limit
        if time.time() - start_time > max_function_time:
            print(f"⏰ Function timeout for {col_name} after {user_timeout_minutes} minutes (user setting), using fallback")
            return generate_fallback_values(column_info, table_name, num_rows)
        
        # Calculate adaptive timeout for this attempt
        attempt_timeout = get_adaptive_timeout(attempt, base_timeout=300)  # Start with 5 minutes
        print(f"🔄 Attempt {attempt + 1} for {col_name} with {attempt_timeout//60}min timeout...")
            
        try:
            response = call_llm(prompt, mode="data_generation")
            
            # Debug: Check if we got a response
            if not response or len(response.strip()) == 0:
                if attempt < max_retries - 1:
                    print(f"⚠️ Empty response for {col_name} (attempt {attempt + 1}), retrying...")
                    continue
                else:
                    print(f"⚠️ Empty response for {col_name} after {max_retries} attempts, using fallback")
                    return generate_fallback_values(column_info, table_name, num_rows)
            
            # Try to extract JSON array from response
            import re
            # Look for JSON array pattern
            json_match = re.search(r'\[[\s\S]*?\]', response)
            if json_match:
                values_json = json_match.group()
                values = json.loads(values_json)
                
                # Clean the values to remove unwanted characters
                cleaned_values = []
                for value in values:
                    if isinstance(value, str):
                        # Remove unwanted characters and clean up
                        cleaned_value = value.strip()
                        # Remove standalone dashes that aren't part of dates
                        if cleaned_value == "-" or cleaned_value == "--":
                            # Replace with appropriate default based on column type
                            if "email" in col_name.lower():
                                cleaned_value = f"user{len(cleaned_values)}@example.com"
                            elif "name" in col_name.lower():
                                cleaned_value = f"Sample Name {len(cleaned_values)}"
                            elif "description" in col_name.lower():
                                cleaned_value = f"Sample description {len(cleaned_values)}"
                            else:
                                cleaned_value = f"Value {len(cleaned_values)}"
                        # Remove leading/trailing dashes but keep date formats
                        elif not re.match(r'\d{4}-\d{2}-\d{2}', cleaned_value):  # Don't touch date formats
                            cleaned_value = cleaned_value.strip('-').strip()
                            if not cleaned_value:  # If empty after cleaning
                                cleaned_value = f"Value {len(cleaned_values)}"
                        cleaned_values.append(cleaned_value)
                    else:
                        cleaned_values.append(value)
                
                values = cleaned_values
                
                if len(values) == num_rows:
                    return values
                elif len(values) > 0:
                    # If we got some values but not enough, extend safely with cycle protection
                    if len(values) < num_rows:
                        original_values = values.copy()
                        cycle_count = 0
                        max_cycles = 10  # Reduced from 50 to prevent long delays
                        
                        while len(values) < num_rows and cycle_count < max_cycles:
                            remaining_needed = num_rows - len(values)
                            to_add = original_values[:min(len(original_values), remaining_needed)]
                            
                            # Safety check: avoid empty additions that would cause infinite loop
                            if not to_add:
                                print(f"⚠️ No values to cycle for {col_name}, breaking extension loop")
                                break
                                
                            values.extend(to_add)
                            cycle_count += 1
                            
                            # Additional safety: if we've cycled too much, break
                            if cycle_count >= max_cycles:
                                print(f"⚠️ Max cycle count reached for {col_name}, switching to fallback generation")
                                break
                        
                        # If we still don't have enough, pad with simple incremental values
                        fallback_count = 0
                        max_fallback_iterations = num_rows * 2  # Absolute safety limit
                        
                        while len(values) < num_rows and fallback_count < max_fallback_iterations:
                            if col_type.upper() in ["INT", "INTEGER", "BIGINT"]:
                                values.append(len(values) + 1)
                            elif col_type.upper() in ["VARCHAR", "TEXT", "STRING"]:
                                values.append(f"Generated_{len(values) + 1}")
                            elif col_type.upper() in ["DATE"]:
                                values.append("2024-01-01")
                            elif col_type.upper() in ["BOOLEAN"]:
                                values.append(len(values) % 2 == 0)
                            else:
                                values.append(f"Value_{len(values) + 1}")
                            
                            fallback_count += 1
                            
                            # Emergency break to prevent true infinite loops
                            if fallback_count >= max_fallback_iterations:
                                print(f"❌ Emergency break: fallback generation limit reached for {col_name}")
                                break
                    
                    return values[:num_rows]
                    
                # If we get here, we successfully got some values - reset consecutive failures
                generate_smart_column_values.consecutive_failures = 0
                return values[:num_rows]
            else:
                if attempt < max_retries - 1:
                    print(f"⚠️ No JSON array found for {col_name} (attempt {attempt + 1}), retrying...")
                    continue
                else:
                    print(f"⚠️ No JSON array found in response for {col_name} after {max_retries} attempts")
                    print(f"📝 Response preview: {response[:100]}...")
                
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"❌ JSON parsing failed for {col_name} (attempt {attempt + 1}): {e}, retrying...")
                continue
            else:
                print(f"❌ JSON parsing failed for {col_name} after {max_retries} attempts: {e}")
                print(f"📝 Response that failed to parse: {response[:200]}...")
        except Exception as e:
            # Enhanced error handling for timeouts and connection issues
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "read timed out" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"⏰ Timeout generating {col_name} (attempt {attempt + 1}), retrying with extended timeout...")
                    continue
                else:
                    print(f"⏰ Timeout generating {col_name} after {max_retries} attempts, using fallback")
            elif "connection" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"🔌 Connection error for {col_name} (attempt {attempt + 1}), retrying...")
                    continue
                else:
                    print(f"🔌 Connection error for {col_name} after {max_retries} attempts: {error_msg}, using fallback")
            else:
                if attempt < max_retries - 1:
                    print(f"❌ Error generating {col_name} (attempt {attempt + 1}): {e}, retrying...")
                    continue
                else:
                    print(f"❌ LLM generation failed for {col_name} after {max_retries} attempts: {e}")
    
    # Fallback to basic generation if all attempts fail
    # Track the failure for circuit breaker
    generate_smart_column_values.failure_count += 1
    generate_smart_column_values.consecutive_failures += 1
    
    print(f"⚠️ All attempts failed for {col_name}, using fallback generation (consecutive failures: {generate_smart_column_values.consecutive_failures})")
    return generate_fallback_values(column_info, table_name, num_rows)

def generate_fallback_values(column_info, table_name, num_rows):
    """
    Enhanced fallback data generation when LLM fails
    """
    col_name = column_info.get("name", "").lower()
    col_type = column_info.get("type", "VARCHAR").upper()
    col_desc = column_info.get("description", "").lower()
    values = []
    
    # Enhanced name patterns
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
                   "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"]
    
    # Enhanced company/business names
    company_names = ["TechCorp", "GlobalSoft", "InnovateLab", "DataSystems", "CloudWorks", "NextGen Solutions",
                     "Digital Dynamics", "SmartTech", "FutureSoft", "ProServices", "Elite Systems", "Prime Tech"]
    
    # Enhanced address components
    street_names = ["Main St", "Oak Ave", "Pine Dr", "Elm St", "First Ave", "Second St", "Park Blvd", 
                    "Cedar Ln", "Maple Dr", "Washington St", "Lincoln Ave", "Jefferson Dr"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio",
              "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus"]
    
    for i in range(num_rows):
        if col_type in ["INT", "INTEGER", "BIGINT"]:
            if "id" in col_name or col_name.endswith("_id"):
                values.append(i + 1)
            elif "age" in col_name:
                values.append(random.randint(18, 80))
            elif "year" in col_name:
                values.append(random.randint(2020, 2024))
            elif "quantity" in col_name or "count" in col_name:
                values.append(random.randint(1, 100))
            elif "score" in col_name or "rating" in col_name:
                values.append(random.randint(1, 10))
            else:
                values.append(random.randint(1, 1000))
                
        elif col_type in ["VARCHAR", "TEXT", "STRING"]:
            if "first_name" in col_name or col_name == "firstname":
                values.append(random.choice(first_names))
            elif "last_name" in col_name or col_name == "lastname":
                values.append(random.choice(last_names))
            elif "name" in col_name and "company" not in col_name:
                values.append(f"{random.choice(first_names)} {random.choice(last_names)}")
            elif "company" in col_name or "business" in col_name or "organization" in col_name:
                values.append(random.choice(company_names))
            elif "email" in col_name:
                domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com", "business.net"]
                first = random.choice(first_names).lower()
                last = random.choice(last_names).lower()
                values.append(f"{first}.{last}@{random.choice(domains)}")
            elif "phone" in col_name or "mobile" in col_name:
                values.append(f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}")
            elif "address" in col_name:
                street_num = random.randint(100, 9999)
                street = random.choice(street_names)
                values.append(f"{street_num} {street}")
            elif "city" in col_name:
                values.append(random.choice(cities))
            elif "state" in col_name:
                states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
                values.append(random.choice(states))
            elif "zip" in col_name or "postal" in col_name:
                values.append(f"{random.randint(10000, 99999)}")
            elif "description" in col_name or "notes" in col_name:
                descriptions = ["High quality product", "Excellent service", "Great value", 
                               "Premium offering", "Standard item", "Basic package"]
                values.append(random.choice(descriptions))
            elif "category" in col_name or "type" in col_name:
                categories = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports", "Automotive"]
                values.append(random.choice(categories))
            else:
                values.append(f"Sample_{col_name}_{i}")
                
        elif col_type in ["DATE"]:
            start_date = datetime(2020, 1, 1)
            end_date = datetime(2024, 12, 31)
            time_between = end_date - start_date
            random_days = random.randrange(time_between.days)
            random_date = start_date + timedelta(days=random_days)
            values.append(random_date.strftime("%Y-%m-%d"))
            
        elif col_type in ["TIMESTAMP"]:
            start_date = datetime(2020, 1, 1)
            end_date = datetime(2024, 12, 31)
            time_between = end_date - start_date
            random_seconds = random.randrange(int(time_between.total_seconds()))
            random_datetime = start_date + timedelta(seconds=random_seconds)
            values.append(random_datetime.strftime("%Y-%m-%d %H:%M:%S"))
            
        elif col_type in ["DECIMAL", "FLOAT", "DOUBLE"]:
            if "price" in col_name or "cost" in col_name or "amount" in col_name:
                values.append(round(random.uniform(10.0, 1000.0), 2))
            elif "percentage" in col_name or "rate" in col_name:
                values.append(round(random.uniform(0.0, 100.0), 2))
            elif "salary" in col_name or "income" in col_name:
                values.append(round(random.uniform(30000.0, 150000.0), 2))
            else:
                values.append(round(random.uniform(1.0, 1000.0), 2))
                
        elif col_type == "BOOLEAN":
            values.append(random.choice([True, False]))
        else:
            values.append(f"Data_{i}")
    
    return values

def categorize_table(table_name, columns):
    """
    Categorize table type based on name patterns and column structure
    """
    table_name_lower = table_name.lower()
    column_names = [col.get("name", "").lower() for col in columns]
    
    # Reference/Lookup tables - typically smaller
    if any(pattern in table_name_lower for pattern in ["reference", "lookup", "category", "type", "status", "country", "state", "currency"]):
        return "reference"
    
    # Master data tables - medium size
    if any(pattern in table_name_lower for pattern in ["customer", "product", "user", "employee", "vendor", "supplier", "client"]):
        return "master_data"
    
    # Check column patterns for better categorization
    has_id_cols = len([col for col in column_names if col.endswith("_id") or col == "id"]) > 0
    has_transaction_cols = any(pattern in " ".join(column_names) for pattern in ["amount", "price", "total", "quantity", "date", "timestamp"])
    has_audit_cols = any(pattern in " ".join(column_names) for pattern in ["created_at", "updated_at", "modified", "version"])
    
    # Transaction/fact tables - larger
    if has_transaction_cols or any(pattern in table_name_lower for pattern in ["order", "transaction", "sale", "payment", "invoice", "purchase"]):
        return "transactional"
    
    # Log/audit tables - can be very large
    if has_audit_cols or any(pattern in table_name_lower for pattern in ["log", "audit", "history", "event", "activity"]):
        return "log_data"
    
    # Default to master data if uncertain
    return "master_data"

def get_suggested_row_count(table_category, base_rows=100):
    """
    Suggest appropriate row counts based on table category
    """
    multipliers = {
        "reference": 0.2,      # 20 rows for reference tables
        "master_data": 1.0,    # 100 rows for master data
        "transactional": 3.0,  # 300 rows for transaction tables
        "log_data": 5.0        # 500 rows for log tables
    }
    
    multiplier = multipliers.get(table_category, 1.0)
    suggested = int(base_rows * multiplier)
    
    # Reasonable bounds
    return max(10, min(suggested, 1000))

def generate_sample_data(schema, num_rows=100, use_ai=False, table_row_counts=None, user_timeout_minutes=15):
    """
    Generate sample data based on the schema with optional AI enhancement and user-controlled timeouts
    """
    data = {}
    
    # Calculate total work for progress tracking
    tables = schema.get("tables", [])
    
    # Total columns is just the sum of all columns across all tables
    total_columns = sum(len(table.get("columns", [])) for table in tables)
    
    # Add overall timeout protection for the entire generation process - much more generous
    import time
    generation_start_time = time.time()
    # Calculate reasonable total timeout: user timeout per column * total columns + buffer
    max_generation_time = (user_timeout_minutes * 60 * total_columns) + 600  # Add 10min buffer
    
    if use_ai and total_columns > 0:
        # Create progress tracking
        progress_bar = st.progress(0)
        status_placeholder = st.empty()  # For showing current table.column
        current_progress = 0
        
        # Reset circuit breaker for new generation session
        if hasattr(generate_smart_column_values, 'consecutive_failures'):
            generate_smart_column_values.consecutive_failures = 0
        
        # Show timeout info
        estimated_total_time = user_timeout_minutes * total_columns
        status_placeholder.info(f"⏰ **Timeout Setting**: {user_timeout_minutes} min/column. Est. max time: {estimated_total_time} minutes for {total_columns} columns")
    
    # Generate data for each table
    for table_idx, table in enumerate(tables):
        # Check overall timeout
        if time.time() - generation_start_time > max_generation_time:
            st.warning(f"⏰ Generation timeout reached ({max_generation_time//3600:.1f} hours). Completing with fallback data...")
            use_ai = False  # Switch to fallback for remaining tables
        
        table_name = table["name"]
        columns = table.get("columns", [])
        
        if not columns:
            continue
        
        # Determine row count for this table
        table_num_rows = table_row_counts.get(table_name, num_rows) if table_row_counts else num_rows
        
        table_data = []
        
        # Pre-generate all column data for consistency and efficiency
        column_data = {}
        for col_idx, col in enumerate(columns):
            col_name = col["name"]
            
            if use_ai:
                # Update progress and show estimated time
                current_progress += 1
                progress_percentage = min(current_progress / total_columns, 1.0)  # Cap at 1.0
                progress_bar.progress(progress_percentage)
                
                # Show current table.column being generated with time estimate
                elapsed_time = time.time() - generation_start_time
                avg_time_per_column = elapsed_time / current_progress if current_progress > 0 else user_timeout_minutes * 60
                remaining_columns = total_columns - current_progress
                estimated_remaining = (avg_time_per_column * remaining_columns) / 60  # Convert to minutes
                
                status_placeholder.info(f"🤖 Generating AI data for **{table_name}.{col_name}** ({current_progress}/{total_columns}) | Est. remaining: {estimated_remaining:.1f} min")
                
                try:
                    column_data[col_name] = generate_smart_column_values(col, table_name, schema, table_num_rows, user_timeout_minutes)
                except Exception as e:
                    # Handle specific timeout errors gracefully in UI
                    error_msg = str(e)
                    if "timeout" in error_msg.lower() or "read timed out" in error_msg.lower():
                        status_placeholder.warning(f"⏰ Timeout on {table_name}.{col_name} - using fallback data")
                    else:
                        status_placeholder.warning(f"⚠️ Error on {table_name}.{col_name} - using fallback data")
                    # Still generate fallback data
                    column_data[col_name] = generate_fallback_values(col, table_name, table_num_rows)
            else:
                column_data[col_name] = generate_fallback_values(col, table_name, table_num_rows)
        
        # Combine into rows
        for row_idx in range(table_num_rows):
            row = {}
            for col in columns:
                col_name = col["name"]
                row[col_name] = column_data[col_name][row_idx]
            table_data.append(row)
            
        data[table_name] = table_data
    
    # Clean up progress indicators
    if use_ai and total_columns > 0:
        progress_bar.progress(1.0)
        status_placeholder.success("✅ AI data generation complete!")
        # Small delay to show completion
        import time
        time.sleep(1.0)
        progress_bar.empty()
        status_placeholder.empty()
    
    return data

def create_excel_download(generated_data):
    """
    Create an Excel file with multiple sheets (one per table)
    """
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for table_name, table_data in generated_data.items():
                if table_data:
                    df = pd.DataFrame(table_data)
                    # Clean sheet name (Excel has restrictions)
                    sheet_name = table_name[:31]  # Max 31 chars
                    sheet_name = sheet_name.replace('/', '_').replace('\\', '_')
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return output.getvalue()
    except ImportError:
        # Fallback if openpyxl not available
        st.error("❌ Excel export requires openpyxl. Installing...")
        return None

def run():
    # Enhanced page header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">🎲 Step 4: Generate & Consolidate Data</h2>
        <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">
            Create realistic datasets and consolidate them into a master view
        </p>
    </div>
    """, unsafe_allow_html=True)

    schema = st.session_state.get("schema")
    if not schema or "tables" not in schema:
        st.error("❌ **No Schema Found**")
        st.markdown("Please create and refine a schema first using the previous steps.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔙 Go to Schema Editor", type="primary", use_container_width=True):
                st.session_state["step"] = "schema_editor"
                st.experimental_rerun()
        return

    # Schema summary
    tables = schema.get("tables", [])
    if tables:
        total_columns = sum(len(table.get("columns", [])) for table in tables)
        
        # Summary cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Tables", len(tables))
        with col2:
            st.metric("🗂️ Total Columns", total_columns)
        with col3:
            st.metric("🔗 Relationships", len(schema.get("relationships", [])))

    # Data generation configuration
    st.markdown("### ⚙️ **Generation Configuration**")
    
    # Generation method selection with enhanced info
    generation_method = st.radio(
        "**Choose Generation Method:**",
        ["🎲 Random Data", "🤖 AI-Enhanced Data"],
        horizontal=True,
        help="AI-Enhanced uses LLM to generate realistic, contextual data"
    )
    
    # Show method description
    if generation_method == "🤖 AI-Enhanced Data":
        st.info("🤖 **AI Mode**: Uses language models to generate contextually appropriate data based on column names, types, and descriptions. More realistic but slower.")
        
        # Add timeout configuration for AI mode
        col1, col2 = st.columns(2)
        with col1:
            user_timeout = st.slider(
                "⏰ **Timeout per Column (minutes)**",
                min_value=1,
                max_value=30,
                value=15,
                help="How long to wait for each column before using fallback data. Local LLMs may need more time."
            )
        with col2:
            st.markdown("#### 📊 **Timeout Guide**")
            st.markdown("""
            - **1-5 min**: Fast cloud APIs
            - **10-15 min**: Local LLMs (recommended)
            - **20+ min**: Very slow/large models
            """)
            
            # Advanced options for power users
            with st.expander("🔧 **Advanced AI Options**"):
                chunk_generation = st.checkbox(
                    "📦 **Chunk Generation**", 
                    value=True,
                    help="Generate data in smaller chunks for better progress tracking"
                )
                allow_mixed_mode = st.checkbox(
                    "🔀 **Mixed Mode**", 
                    value=True,
                    help="Use AI for some columns and fallback for others if timeouts occur"
                )
    else:
        st.info("🎲 **Random Mode**: Fast generation using predefined patterns and random values. Good for testing and prototyping.")
        user_timeout = 15  # Default for random mode
    
    # Individual table configuration
    table_row_counts = {}
    default_rows = 100  # Set default internally
    
    if tables:
        # Categorize tables and show in groups
        categorized_tables = {}
        for table in tables:
            table_name = table["name"]
            columns = table.get("columns", [])
            category = categorize_table(table_name, columns)
            
            if category not in categorized_tables:
                categorized_tables[category] = []
            categorized_tables[category].append(table)
        
        # Display categories in a nice order
        category_order = ["reference", "master_data", "transactional", "log_data"]
        category_icons = {
            "reference": "📚",
            "master_data": "👥", 
            "transactional": "💰",
            "log_data": "📝"
        }
        category_descriptions = {
            "reference": "Reference/Lookup Tables",
            "master_data": "Master Data Tables", 
            "transactional": "Transactional/Fact Tables",
            "log_data": "Log/Audit Tables"
        }
        
        # Table Volume Configuration - Collapsible with WOW factor
        with st.expander("📊 **Table Volume Configuration**", expanded=True):
            # Enhanced title styling
            st.markdown("""
            <style>
            .stExpander > div:first-child > div:first-child > p {
                font-size: 20px !important;
                font-weight: 600 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.info("💡 **Smart Sizing**: Configure row counts for each table. Different table types get intelligent suggestions based on their purpose.")
            
            # Smart suggestions toggle
            use_smart_suggestions = st.checkbox(
                "🧠 Use intelligent suggestions",
                value=True,
                help="Automatically suggest appropriate row counts based on table type (reference, master data, transactional, etc.)"
            )
            
            # Custom CSS for sleek horizontal row design
            st.markdown("""
            <style>
            .config-container {
                background: #1a1a1a;
                border-radius: 8px;
                padding: 16px;
                margin: 8px 0;
                border: 1px solid #333;
            }
            .table-row {
                display: flex;
                align-items: center;
                padding: 12px;
                margin: 4px 0;
                background: linear-gradient(90deg, #2a2a2a 0%, #2d2d2d 100%);
                border-radius: 6px;
                border-left: 4px solid;
                transition: all 0.2s ease;
            }
            .table-row:hover {
                background: linear-gradient(90deg, #333 0%, #363636 100%);
                transform: translateX(2px);
            }
            .table-row.reference { border-left-color: #f97316; }
            .table-row.master_data { border-left-color: #3b82f6; }
            .table-row.transactional { border-left-color: #10b981; }
            .table-row.log_data { border-left-color: #8b5cf6; }
            
            .table-info {
                flex: 1;
                color: #fff;
            }
            .table-name {
                font-weight: 600;
                font-size: 16px;
                margin-bottom: 2px;
            }
            .table-meta {
                font-size: 12px;
                color: #888;
            }
            .category-pill {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: 500;
                margin-left: 8px;
            }
            .category-pill.reference { background: rgba(249, 115, 22, 0.2); color: #fb923c; }
            .category-pill.master_data { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
            .category-pill.transactional { background: rgba(16, 185, 129, 0.2); color: #34d399; }
            .category-pill.log_data { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
            
            .size-indicator {
                width: 80px;
                height: 6px;
                background: #333;
                border-radius: 3px;
                margin: 0 16px;
                position: relative;
                overflow: hidden;
            }
            .size-bar {
                height: 100%;
                border-radius: 3px;
                transition: width 0.3s ease;
            }
            .size-bar.small { width: 25%; background: #f97316; }
            .size-bar.medium { width: 50%; background: #3b82f6; }
            .size-bar.large { width: 75%; background: #10b981; }
            .size-bar.xlarge { width: 100%; background: #8b5cf6; }
            </style>
            """, unsafe_allow_html=True)
            
            # Create container for all table configurations
            with st.container():
                st.markdown('<div class="config-container">', unsafe_allow_html=True)
                
                # Header row
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1, 1])
                with col1:
                    st.markdown("**Table & Category**")
                with col2:
                    st.markdown("**Size**")
                with col3:
                    st.markdown("**Suggested**")
                with col4:
                    st.markdown("**Rows**")
                with col5:
                    st.markdown("**Actions**")
                
                st.markdown("---")
                
                # Display each table as a sleek row
                for table in tables:
                    table_name = table["name"]
                    columns = table.get("columns", [])
                    col_count = len(columns)
                    category = categorize_table(table_name, columns)
                    
                    # Get category info
                    category_display = category_descriptions.get(category, category.title())
                    category_icon = category_icons.get(category, "📋")
                    suggested_rows = get_suggested_row_count(category, default_rows) if use_smart_suggestions else default_rows
                    
                    # Determine size category for visual indicator
                    if suggested_rows <= 50:
                        size_class = "small"
                        size_label = "Small"
                    elif suggested_rows <= 150:
                        size_class = "medium" 
                        size_label = "Medium"
                    elif suggested_rows <= 400:
                        size_class = "large"
                        size_label = "Large"
                    else:
                        size_class = "xlarge"
                        size_label = "X-Large"
                    
                    # Table row with inline controls
                    col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1, 1])
                    
                    with col1:
                        # Table info with category
                        st.markdown(f"""
                        <div class="table-row {category}">
                            <div class="table-info">
                                <div class="table-name">📋 {table_name}</div>
                                <div class="table-meta">
                                    {col_count} columns
                                    <span class="category-pill {category}">{category_icon} {category_display}</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        # Size indicator bar
                        st.markdown(f"""
                        <div style="padding: 20px 0;">
                            <div class="size-indicator">
                                <div class="size-bar {size_class}"></div>
                            </div>
                            <div style="text-align: center; color: #888; font-size: 11px; margin-top: 4px;">
                                {size_label}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        # Suggested value
                        st.markdown(f"""
                        <div style="padding: 20px 0; text-align: center;">
                            <div style="color: #10b981; font-weight: 600;">{suggested_rows}</div>
                            <div style="color: #666; font-size: 10px;">suggested</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        # Row count input (compact)
                        table_row_counts[table_name] = st.number_input(
                            "",
                            min_value=10,
                            max_value=10000,
                            value=suggested_rows,
                            step=10,
                            key=f"rows_{table_name}",
                            help=f"Rows for {table_name}",
                            label_visibility="collapsed"
                        )
                    
                    with col5:
                        # Quick actions
                        if st.button("🔄", key=f"reset_{table_name}", help="Reset to suggested"):
                            st.session_state[f"rows_{table_name}"] = suggested_rows
                            st.experimental_rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Show generation summary
    if table_row_counts:
        total_rows = sum(table_row_counts.values())
        total_columns = sum(len(table.get("columns", [])) for table in tables)
        avg_rows = total_rows / len(tables) if tables else 0
        
        st.markdown("#### 📊 **Generation Summary**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Tables", len(tables))
        with col2:
            st.metric("📏 Total Rows", total_rows)
        with col3:
            st.metric("🗂️ Total Columns", total_columns)
        with col4:
            st.metric("📈 Avg Rows/Table", f"{avg_rows:.0f}")
        
        # Show estimated time for AI generation
        if generation_method == "🤖 AI-Enhanced Data":
            estimated_time_min = total_columns * (user_timeout * 0.7)  # Assume 70% of max timeout on average
            if estimated_time_min > 60:
                st.metric("⏱️ Estimated Time", f"~{estimated_time_min/60:.1f}h", help="Estimated time based on timeout setting")
            else:
                st.metric("⏱️ Estimated Time", f"~{estimated_time_min:.0f}m", help="Estimated time based on timeout setting")
    else:
        # Fallback message when no tables configured
        st.warning("⚠️ No tables available for configuration. Please create a schema first.")

    # Advanced options
    with st.expander("🔧 **Advanced Options**"):
        col1, col2 = st.columns(2)
        with col1:
            seed = st.number_input(
                "Random seed (for reproducibility):",
                min_value=0,
                value=42,
                help="Use the same seed to generate identical data"
            )
            
        with col2:
            include_nulls = st.checkbox(
                "Include NULL values",
                value=False,
                help="Randomly include NULL values in some fields"
            )

    # Generate data button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Generate Synthetic Data", type="primary", use_container_width=True):
            if seed:
                random.seed(seed)
                
            use_ai = generation_method == "🤖 AI-Enhanced Data"
            
            # Use per-table row counts if available, otherwise fallback to default
            final_row_counts = table_row_counts if table_row_counts else None
            final_default_rows = default_rows
            
            with st.spinner("🔮 Generating your synthetic dataset..."):
                try:
                    # Generate the data
                    generated_data = generate_sample_data(
                        schema, 
                        final_default_rows, 
                        use_ai=use_ai,
                        table_row_counts=final_row_counts,
                        user_timeout_minutes=user_timeout if generation_method == "🤖 AI-Enhanced Data" else 5
                    )
                    st.session_state["generated_data"] = generated_data
                    
                    if use_ai:
                        st.success("✅ AI-enhanced synthetic data generated successfully! 🤖")
                    else:
                        st.success("✅ Random synthetic data generated successfully! 🎲")
                    
                    # Show generation summary
                    if final_row_counts:
                        total_generated = sum(len(data) for data in generated_data.values())
                        st.info(f"📊 Generated {total_generated} total rows across {len(generated_data)} tables with individual sizing!")
                    
                    # Auto-trigger consolidation
                    st.experimental_rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error generating data: {str(e)}")
                    return

    # Consolidation section - show if data is generated
    if "generated_data" in st.session_state:
        generated_data = st.session_state["generated_data"]
        
        st.markdown("### 🔗 **Data Consolidation**")
        st.info("💡 **Next Step**: Consolidate your individual tables into a master dataset for better analysis and business rule application.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔗 Consolidate into Master Dataset", type="primary", use_container_width=True):
                with st.spinner("🔄 Consolidating tables using foreign key relationships..."):
                    try:
                        consolidated_df = consolidate_data(generated_data, schema)
                        if not consolidated_df.empty:
                            st.session_state["consolidated_data"] = consolidated_df
                            st.success("✅ Data successfully consolidated into master dataset!")
                            st.info("🎯 **Ready for Analysis**: Your consolidated dataset is ready for visual exploration and business rule enhancement!")
                        else:
                            st.error("❌ Failed to consolidate data. Please check your table relationships.")
                    except Exception as e:
                        st.error(f"❌ Error consolidating data: {str(e)}")

    # Show consolidated data preview
    if "consolidated_data" in st.session_state:
        consolidated_df = st.session_state["consolidated_data"]
        
        st.markdown("### 🎯 **Master Dataset Preview**")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📏 Rows", len(consolidated_df))
        with col2:
            st.metric("📋 Columns", len(consolidated_df.columns))
        with col3:
            st.metric("💾 Size", f"{consolidated_df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        with col4:
            missing_cells = consolidated_df.isnull().sum().sum()
            st.metric("🕳️ Missing Values", missing_cells)
        
        # Data preview
        st.markdown("#### 👀 **Consolidated Data Sample**")
        st.dataframe(consolidated_df.head(10), use_container_width=True)
        
        # Quick insights
        st.markdown("#### 📊 **Quick Insights**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔍 Column Overview:**")
            numeric_cols = len(consolidated_df.select_dtypes(include=['number']).columns)
            text_cols = len(consolidated_df.select_dtypes(include=['object']).columns)
            date_cols = len(consolidated_df.select_dtypes(include=['datetime']).columns)
            st.write(f"• **Numeric columns:** {numeric_cols}")
            st.write(f"• **Text columns:** {text_cols}")
            st.write(f"• **Date columns:** {date_cols}")
        
        with col2:
            st.markdown("**🎯 Data Quality:**")
            completeness = ((len(consolidated_df) * len(consolidated_df.columns)) - missing_cells) / (len(consolidated_df) * len(consolidated_df.columns)) * 100
            st.write(f"• **Data completeness:** {completeness:.1f}%")
            unique_rows = len(consolidated_df.drop_duplicates())
            st.write(f"• **Unique rows:** {unique_rows}/{len(consolidated_df)}")
            
        # Next step guidance
        st.markdown("---")
        st.markdown("### 🚀 **Ready for Enhancement**")
        st.info("🔬 **Next**: Move to 'Augment Data' to explore your consolidated dataset visually and apply intelligent business rules!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔬 Go to Augment Data", type="primary", use_container_width=True):
                st.session_state["step"] = "augment_data"
                st.experimental_rerun()
        
        # Export options for consolidated data
        st.markdown("### 📤 **Export Consolidated Dataset**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_data = consolidated_df.to_csv(index=False)
            st.download_button(
                label="📁 Download Consolidated CSV",
                data=csv_data,
                file_name="consolidated_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            json_data = consolidated_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📁 Download Consolidated JSON",
                data=json_data,
                file_name="consolidated_data.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            # Excel export for consolidated data
            excel_output = io.BytesIO()
            try:
                with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
                    consolidated_df.to_excel(writer, sheet_name='Consolidated_Data', index=False)
                excel_output.seek(0)
                st.download_button(
                    label="📊 Download Consolidated Excel",
                    data=excel_output.getvalue(),
                    file_name="consolidated_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception:
                st.button("📊 Excel (Unavailable)", disabled=True, use_container_width=True)

    # Display individual table data (show by default when no consolidation yet)
    if "generated_data" in st.session_state:
        generated_data = st.session_state["generated_data"]
        
        # Show expanded by default if no consolidated data exists
        expanded_default = "consolidated_data" not in st.session_state
        
        with st.expander("📊 **Individual Table Preview & Verification**", expanded=expanded_default):
            st.info("🔍 **Verification Step**: Review your individual tables before consolidation to ensure data quality and relationships.")
            
            # Table selector for preview
            table_names = list(generated_data.keys())
            if table_names:
                # Show all tables in tabs for better overview
                if len(table_names) <= 4:
                    # Use tabs for small number of tables
                    tabs = st.tabs([f"📋 {name}" for name in table_names])
                    for idx, (tab, table_name) in enumerate(zip(tabs, table_names)):
                        with tab:
                            if table_name in generated_data:
                                table_data = generated_data[table_name]
                                
                                if table_data:
                                    df = pd.DataFrame(table_data)
                                    
                                    # Data summary
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("📏 Rows", len(df))
                                    with col2:
                                        st.metric("📋 Columns", len(df.columns))
                                    with col3:
                                        st.metric("💾 Size", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
                                    
                                    # Data preview
                                    st.markdown(f"#### 👀 **Data Sample**")
                                    st.dataframe(df.head(10), use_container_width=True)
                                    
                                    # Show data types and sample values
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown("**🔧 Column Info:**")
                                        col_info = []
                                        for col in df.columns:
                                            col_info.append({
                                                "Column": col,
                                                "Type": str(df[col].dtype),
                                                "Unique": df[col].nunique(),
                                                "Sample": str(df[col].iloc[0]) if len(df) > 0 else "N/A"
                                            })
                                        st.dataframe(pd.DataFrame(col_info), use_container_width=True)
                                    
                                    with col2:
                                        st.markdown("**📊 Quick Stats:**")
                                        numeric_cols = df.select_dtypes(include=['number']).columns
                                        if len(numeric_cols) > 0:
                                            st.dataframe(df[numeric_cols].describe().round(2))
                                        else:
                                            st.info("No numeric columns in this table")
                else:
                    # Use selectbox for many tables
                    selected_table = st.selectbox(
                        "Select table to preview:",
                        table_names,
                        help="Choose which table's data to preview"
                    )
                    
                    if selected_table and selected_table in generated_data:
                        table_data = generated_data[selected_table]
                        
                        if table_data:
                            df = pd.DataFrame(table_data)
                            
                            # Data summary
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("📏 Rows", len(df))
                            with col2:
                                st.metric("📋 Columns", len(df.columns))
                            with col3:
                                st.metric("💾 Size", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
                            
                            # Data preview
                            st.markdown(f"#### 👀 **Preview: `{selected_table}` table**")
                            st.dataframe(df.head(20), use_container_width=True)

        # Export options for individual tables
        st.markdown("#### 📤 **Export Individual Tables**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Download JSON", use_container_width=True):
                json_data = json.dumps(generated_data, indent=2, default=str)
                st.download_button(
                    label="📁 Download JSON",
                    data=json_data,
                    file_name="synthetic_data.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Download CSV", use_container_width=True):
                # Convert each table to CSV
                for table_name, table_data in generated_data.items():
                    if table_data:
                        df = pd.DataFrame(table_data)
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label=f"📁 Download {table_name}.csv",
                            data=csv,
                            file_name=f"{table_name}.csv",
                            mime="text/csv"
                        )
        
        with col3:
            if st.button("� Download Excel", use_container_width=True):
                excel_data = create_excel_download(generated_data)
                if excel_data:
                    st.download_button(
                        label="📁 Download Excel Workbook",
                        data=excel_data,
                        file_name="synthetic_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("Failed to create Excel file. Please try CSV export instead.")
        
        with col4:
            if st.button("🔄 Regenerate", use_container_width=True):
                for key in ["generated_data", "consolidated_data"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_rerun()

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔙 Back to Editor", use_container_width=True):
            st.session_state["step"] = "schema_editor"
            st.experimental_rerun()
    
    with col2:
        if st.button("🔬 Next: Augment Data", use_container_width=True):
            st.session_state["step"] = "augment_data"
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
