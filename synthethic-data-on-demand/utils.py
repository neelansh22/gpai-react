import streamlit as st
import requests
import google.generativeai as genai
import json, re
import graphviz
from streamlit_agraph import agraph, Node, Edge, Config
###########################################################################

def test_local_llm_connection(address, port):
    """
    Test connection to local LLM server with detailed diagnostics
    """
    st.info(f"🔍 **Connection Diagnostics for {address}:{port}**")
    
    # Test 1: Basic HTTP connectivity
    try:
        url = f"http://{address}:{port}"
        response = requests.get(url, timeout=10)
        st.success(f"✅ HTTP connection successful (Status: {response.status_code})")
        
        # Test 2: Check available models
        try:
            models_url = f"http://{address}:{port}/v1/models"
            models_response = requests.get(models_url, timeout=10)
            if models_response.status_code == 200:
                st.success("✅ Models endpoint accessible")
                models_data = models_response.json()
                if "data" in models_data and models_data["data"]:
                    available_models = [m.get('id', 'unknown') for m in models_data['data']]
                    st.info(f"📋 Available models: {', '.join(available_models)}")
                    
                    # Check if our target model is available
                    if "lfm2-700m" in available_models:
                        st.success("✅ Target model 'lfm2-700m' is available")
                    else:
                        st.warning(f"⚠️ Target model 'lfm2-700m' not found. Available: {available_models}")
                else:
                    st.warning("⚠️ No models found in response")
            else:
                st.warning(f"⚠️ Models endpoint returned status {models_response.status_code}")
        except Exception as e:
            st.warning(f"⚠️ Could not check models endpoint: {str(e)}")
        
        # Test 3: Test chat completions endpoint with a simple request
        try:
            st.info("🧪 Testing chat completions endpoint...")
            chat_url = f"http://{address}:{port}/v1/chat/completions"
            test_payload = {
                "model": "lfm2-700m",  # Updated to match actual model name
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "max_tokens": 10,  # Very small for quick test
                "temperature": 0.1,
                "stream": False
            }
            
            chat_response = requests.post(
                chat_url,
                headers={"Content-Type": "application/json"},
                json=test_payload,
                timeout=60  # Increased timeout to 60 seconds
            )
            
            if chat_response.status_code == 200:
                result = chat_response.json()
                st.success("✅ Chat completions endpoint working!")
                
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                    st.info(f"📝 Test response: {content}")
                    st.success("✅ Model is responding (basic functionality confirmed)")
                else:
                    st.warning("⚠️ Unexpected response format from chat endpoint")
                    st.json(result)
            else:
                st.error(f"❌ Chat completions failed: HTTP {chat_response.status_code}")
                st.error(f"Response: {chat_response.text}")
                
        except requests.exceptions.Timeout:
            st.error("❌ Chat completions test timed out after 60 seconds")
            st.info("💡 **This indicates the model is slow but functional**")
            st.info("• LFM2-700M should be much faster than this")
            st.info("• Consider using Google Gemini for fastest results")
            st.info("• The model will work but may need optimization")
        except Exception as e:
            st.error(f"❌ Chat completions test failed: {str(e)}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to {address}:{port}")
        st.info("💡 **Possible issues:**")
        st.info(f"• LM Studio not running on {address}")
        st.info(f"• Server not configured to listen on {port}")
        st.info(f"• Firewall blocking port {port}")
        st.info(f"• Network connectivity issues")
        return False
        
    except requests.exceptions.Timeout:
        st.error(f"❌ Connection timeout to {address}:{port}")
        st.info("💡 Server may be overloaded or very slow")
        return False
        
    except Exception as e:
        st.error(f"❌ Connection test failed: {str(e)}")
        return False


def handle_streaming_response(url, payload, mode="schema"):
    """
    Handle streaming LLM responses to detect and parse JSON in real-time
    """
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=(300, 900) if mode == "data_generation" else (120, 300)  # (connect, read) timeouts - 15min read for data gen
        )
        
        if response.status_code != 200:
            st.error(f"❌ Streaming request failed: {response.status_code}")
            return None
        
        accumulated_content = ""
        json_started = False
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False
        last_char = ""
        
        # Create a placeholder for live updates
        status_placeholder = st.empty()
        update_counter = 0
        
        # For data generation, add early termination when we detect complete JSON array
        max_iterations = 1000 if mode == "data_generation" else 10000  # Limit iterations
        iteration_count = 0
        
        # Add timeout mechanism within streaming loop
        import time
        start_time = time.time()
        max_streaming_time = 60 if mode == "data_generation" else 300  # 1 min for data gen, 5 min for others
        
        for line in response.iter_lines(decode_unicode=True):
            iteration_count += 1
            current_time = time.time()
            
            # Check timeouts
            if iteration_count > max_iterations:
                print(f"⚠️ Streaming iteration limit reached ({max_iterations}) for {mode}")
                break
            if current_time - start_time > max_streaming_time:
                print(f"⚠️ Streaming time limit reached ({max_streaming_time}s) for {mode}")
                break
                
            if not line:
                continue
                
            # Handle different streaming formats
            content_delta = ""
            
            # OpenAI-compatible Server-Sent Events format
            if line.startswith("data: "):
                try:
                    data_str = line[6:].strip()  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break
                    
                    chunk_data = json.loads(data_str)
                    
                    # Extract content from OpenAI-compatible format
                    if "choices" in chunk_data and chunk_data["choices"]:
                        delta = chunk_data["choices"][0].get("delta", {})
                        content_delta = delta.get("content", "")
                    elif "message" in chunk_data:
                        content_delta = chunk_data["message"].get("content", "")
                        
                except json.JSONDecodeError:
                    # Skip malformed chunk data
                    continue
                except Exception as e:
                    continue
            
            # Handle raw text streaming (some local LLMs)
            elif not line.startswith("event:") and not line.startswith("id:"):
                try:
                    # Try to parse as JSON chunk
                    chunk_data = json.loads(line)
                    if "content" in chunk_data:
                        content_delta = chunk_data["content"]
                    elif "text" in chunk_data:
                        content_delta = chunk_data["text"]
                except:
                    # Treat as raw text
                    content_delta = line
            
            if content_delta:
                accumulated_content += content_delta
                
                # Track JSON structure in real-time with better logic
                for char in content_delta:
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\' and in_string:
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                    
                    if not in_string:
                        if char == '{':
                            if not json_started:
                                json_started = True
                                if mode != "data_generation":  # Only show info for non-data-generation modes
                                    st.info("🔄 JSON object detected, starting real-time parsing...")
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        elif char == '[':
                            if not json_started:
                                json_started = True
                                if mode != "data_generation":  # Only show info for non-data-generation modes
                                    st.info("🔄 JSON array detected, starting real-time parsing...")
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                    
                    last_char = char
                
                # Update status every 50 chunks to avoid too much UI churn
                update_counter += 1
                if update_counter % 50 == 0 and mode != "data_generation":  # Only show status for non-data-generation modes
                    status_placeholder.info(f"📡 Streaming: {len(accumulated_content)} chars | Braces: {brace_count} | Brackets: {bracket_count} | In string: {in_string}")
                
                # Check if JSON structure looks complete and valid
                if json_started and brace_count == 0 and bracket_count == 0 and not in_string:
                    # Try to parse the accumulated content
                    try:
                        test_content = accumulated_content.strip()
                        if test_content:
                            # Remove common prefixes/suffixes
                            if test_content.startswith("```json"):
                                test_content = test_content[7:].strip()
                            elif test_content.startswith("```"):
                                test_content = test_content[3:].strip()
                            if test_content.endswith("```"):
                                test_content = test_content[:-3].strip()
                            
                            # Clean up common issues
                            test_content = re.sub(r',(\s*[}\]])', r'\1', test_content)  # Remove trailing commas
                            
                            # Validate JSON
                            parsed = json.loads(test_content)
                            
                            # Validate structure based on mode
                            if mode == "schema":
                                if isinstance(parsed, dict) and "tables" in parsed:
                                    tables = parsed.get("tables", [])
                                    if isinstance(tables, list) and len(tables) > 0:
                                        # Validate that tables have required structure
                                        valid_tables = all(isinstance(t, dict) and "name" in t and "columns" in t for t in tables)
                                        if valid_tables:
                                            if mode != "data_generation":  # Only show success for non-data-generation modes
                                                status_placeholder.success(f"✅ Complete schema with {len(tables)} tables detected!")
                                            return accumulated_content
                                elif isinstance(parsed, list) and len(parsed) > 0:
                                    # Check if it's an array of tables
                                    valid_tables = all(isinstance(t, dict) and "name" in t and "columns" in t for t in parsed)
                                    if valid_tables:
                                        if mode != "data_generation":  # Only show success for non-data-generation modes
                                            status_placeholder.success(f"✅ Complete table array with {len(parsed)} tables detected!")
                                        return accumulated_content
                            elif mode == "questions":
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    # Check if questions have required structure
                                    valid_questions = [q for q in parsed if isinstance(q, dict) and "question" in q]
                                    if len(valid_questions) >= 2:  # At least 2 valid questions
                                        if mode != "data_generation":  # Only show success for non-data-generation modes
                                            status_placeholder.success(f"✅ Complete questions array with {len(valid_questions)} questions detected!")
                                        return accumulated_content
                                elif isinstance(parsed, dict) and "questions" in parsed:
                                    questions = parsed.get("questions", [])
                                    valid_questions = [q for q in questions if isinstance(q, dict) and "question" in q]
                                    if len(valid_questions) >= 2:
                                        if mode != "data_generation":  # Only show success for non-data-generation modes
                                            status_placeholder.success(f"✅ Complete questions object with {len(valid_questions)} questions detected!")
                                        return accumulated_content
                            elif mode == "data_generation":
                                # For data generation, any valid JSON array is good - terminate early
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    return accumulated_content
                            else:
                                # For other modes, any valid JSON is good
                                if mode != "data_generation":  # Only show success for non-data-generation modes
                                    status_placeholder.success("✅ Complete JSON structure detected!")
                                return accumulated_content
                    except json.JSONDecodeError:
                        # JSON not complete yet, continue streaming
                        pass
                    except Exception as e:
                        # Some other validation error, continue streaming
                        pass
        
        # End of stream reached
        status_placeholder.info("📡 Streaming completed, processing final content...")
        
        if accumulated_content.strip():
            return accumulated_content
        else:
            st.warning("⚠️ No content received from streaming response")
            return None
    
    except Exception as e:
        st.error(f"❌ Streaming handler error: {str(e)}")
        return None

###########################################################################

def call_llm(prompt, mode="schema"):
    """
    Enhanced LLM calling with better prompting for both Gemini and local LLMs
    """
    llm_source = st.session_state.get("llm_source", "Google Gemini")
    
    # Add consistent formatting instructions optimized for both Gemini and Qwen2.5
    if llm_source == "Google Gemini":
        format_instruction = "\n\nIMPORTANT: Please respond with valid JSON only. Do not include any explanations, code blocks, or additional text. Just return the pure JSON object/array."
    else:
        # Enhanced prompt for local LLM emphasizing JSON integrity
        if mode == "schema":
            format_instruction = "\n\nCRITICAL: Return ONLY valid, complete JSON. Ensure ALL quotes are properly closed. No explanations. If response gets cut off, prioritize completing the JSON structure properly."
        else:
            format_instruction = "\n\nReturn valid, complete JSON only. Ensure all quotes and brackets are properly closed. No explanations."
    
    enhanced_prompt = prompt + format_instruction
    
    if llm_source == "Google Gemini":
        try:
            api_key = st.session_state.get("google_api_key", "")
            if not api_key:
                st.error("❌ Google Gemini API key is required")
                return ""
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(enhanced_prompt)
            return response.text
        except Exception as e:
            st.error(f"❌ Google Gemini API error: {str(e)}")
            return ""
    else:
        try:
            address = st.session_state.get("local_llm_address", "192.168.1.16")  # Remote LM Studio server
            port = st.session_state.get("local_llm_port", "1234")
            
            if not address or not port:
                st.error("❌ Local LLM address and port are required")
                return ""
            
            url = f"http://{address}:{port}/v1/chat/completions"
            
            # Simplified connection - just try the request directly
            # Adjust token limits based on task complexity
            token_limits = {
                "schema": 50000,         # INCREASED: Complex schemas need much more space
                "questions": 10000,      # Questions are shorter
                "autofill": 15000,       # Table autofill is medium complexity
                "estimation": 10000,     # Row count estimates are concise
                "data_generation": 50000  # Column data generation is simple and repetitive
            }
            max_tokens = token_limits.get(mode, 1500)
            max_retries = 2
            
            for attempt in range(max_retries):
                # For data generation, skip streaming and use direct API call for speed
                if mode == "data_generation":
                    try:
                        response = requests.post(
                            url,
                            headers={"Content-Type": "application/json"},
                            json={
                                "model": "lfm2-700m",
                                "messages": [
                                    {
                                        "role": "system", 
                                        "content": "You are a helpful assistant. Always respond with valid JSON only."
                                    },
                                    {
                                        "role": "user", 
                                        "content": enhanced_prompt
                                    }
                                ],
                                "stream": False,  # No streaming for data generation
                                "temperature": 0.3,
                                "max_tokens": max_tokens,
                                "top_p": 0.9,
                                "stop": ["User:", "Human:", "Assistant:", "---"]
                            },
                            timeout=90  # 90 seconds should be plenty for data generation
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if "choices" in result and result["choices"]:
                                content = result["choices"][0]["message"]["content"]
                                if content and len(content.strip()) > 10:
                                    return content
                        
                        # If that didn't work, fall through to streaming approach
                    except Exception as e:
                        print(f"Direct API failed for data generation: {e}")
                        # Fall through to streaming
                
                # Try streaming for non-data-generation or as fallback
                try:
                    streaming_result = handle_streaming_response(url, {
                        "model": "lfm2-700m",
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are a senior database architect and domain expert. Create detailed, realistic database schemas that accurately reflect the specific domain and business requirements. Always respond with valid JSON only." if mode == "schema" else "You are a helpful assistant. Always respond with valid JSON."
                            },
                            {
                                "role": "user", 
                                "content": enhanced_prompt
                            }
                        ],
                        "stream": True,  # Enable streaming
                        "temperature": 0.3,
                        "max_tokens": max_tokens,
                        "top_p": 0.9,
                        "stop": ["User:", "Human:", "Assistant:", "---"]
                    }, mode)
                    
                    if streaming_result:
                        if mode != "data_generation":  # Only show success message for non-data-generation modes
                            st.success(f"✅ Streaming response completed ({len(streaming_result)} chars) - attempt {attempt + 1}")
                        return streaming_result
                    else:
                        if mode != "data_generation":  # Only show warning for non-data-generation modes
                            st.warning(f"⚠️ Streaming failed, falling back to non-streaming... (attempt {attempt + 1})")
                except Exception as e:
                    if mode != "data_generation":  # Only show warning for non-data-generation modes
                        st.warning(f"⚠️ Streaming error: {str(e)}. Falling back to non-streaming...")
                
                # Fallback to non-streaming response
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": "lfm2-700m",  # Updated to match actual model name
                        "messages": [
                            {
                                "role": "system", 
                                "content": "You are a senior database architect and domain expert. Create detailed, realistic database schemas that accurately reflect the specific domain and business requirements. Always respond with valid JSON only." if mode == "schema" else "You are a helpful assistant. Always respond with valid JSON."
                            },
                            {
                                "role": "user", 
                                "content": enhanced_prompt
                            }
                        ],
                        "stream": False,
                        "temperature": 0.3,  # Slightly higher for more creativity in domain modeling
                        "max_tokens": max_tokens,  # Dynamic based on task complexity
                        "top_p": 0.9,        # Add nucleus sampling
                        "stop": ["User:", "Human:", "Assistant:", "---"]  # Better stop tokens
                    },
                    timeout=(300, 900) if mode == "data_generation" else (120, 300)  # (connect, read) - 15min read for data gen
                )
                
                if response.status_code != 200:
                    st.error(f"❌ Local LLM HTTP error {response.status_code}: {response.text}")
                    return ""
                
                result = response.json()
                
                # Try OpenAI-compatible "choices" first
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                    st.success(f"✅ Received response from local LLM ({len(content)} chars) - attempt {attempt + 1}")
                    
                    # Enhanced validation for JSON integrity
                    content_stripped = content.strip()
                    
                    # Check for incomplete responses and retry
                    if len(content_stripped) < 20:
                        if attempt < max_retries - 1:
                            st.warning(f"⚠️ Response too short, retrying... (attempt {attempt + 1})")
                            continue
                        else:
                            st.warning(f"⚠️ Response seems incomplete: '{content}'")
                            st.info("💡 Try: 1) Simpler prompt 2) Google Gemini 3) Check LM Studio settings")
                            return ""
                    
                    # Check for JSON integrity issues before returning
                    json_issues = []
                    if content_stripped.startswith('[') and not content_stripped.endswith(']'):
                        json_issues.append("Missing closing bracket ]")
                    if content_stripped.startswith('{') and not content_stripped.endswith('}'):
                        json_issues.append("Missing closing brace }")
                    
                    # Count quotes to detect truncated strings
                    quote_count = content_stripped.count('"')
                    if quote_count % 2 != 0:
                        json_issues.append("Odd number of quotes - likely truncated string")
                    
                    # Check for obvious truncation patterns
                    if content_stripped.endswith('"...') or content_stripped.endswith('",') or content_stripped.endswith('"'):
                        if not (content_stripped.endswith('"}') or content_stripped.endswith('"]')):
                            json_issues.append("Response appears truncated")
                    
                    if json_issues and attempt < max_retries - 1:
                        st.warning(f"⚠️ JSON integrity issues detected: {', '.join(json_issues)}. Retrying with more tokens...")
                        # Increase tokens for retry
                        max_tokens = int(max_tokens * 1.5)
                        continue
                    elif json_issues:
                        st.warning(f"⚠️ JSON integrity issues: {', '.join(json_issues)}. Proceeding with repair attempt...")
                    
                    return content
                # Fallback to Ollama-style "message"
                elif "message" in result:
                    content = result["message"].get("content", "")
                    if len(content.strip()) >= 20:
                        return content
                    elif attempt < max_retries - 1:
                        st.warning(f"⚠️ Response too short, retrying... (attempt {attempt + 1})")
                        continue
                    else:
                        st.warning(f"⚠️ Response seems incomplete: '{content}'")
                        return ""
                else:
                    if attempt < max_retries - 1:
                        st.warning(f"⚠️ Unexpected response format, retrying... (attempt {attempt + 1})")
                        continue
                    else:
                        st.error(f"❌ Unexpected local LLM response format: {result}")
                        return ""
            
            # If we get here, all retries failed
            st.error("❌ All retry attempts failed")
            return ""
                
        except requests.exceptions.Timeout:
            timeout_duration = "15 minutes" if mode == "data_generation" else "5 minutes"
            if mode == "data_generation":
                # For data generation, don't show error in UI, just return empty to trigger fallback
                print(f"❌ Local LLM request timed out after {timeout_duration} for data generation")
                return ""
            else:
                st.error(f"❌ Local LLM request timed out after {timeout_duration}.")
                st.info("💡 **The request took longer than expected:**")
                st.info("• Try using simpler prompts or Google Gemini for complex operations")
                st.info("• Check LM Studio performance settings")  
                st.info("• Consider breaking complex requests into smaller parts")
                return ""
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to local LLM at {address}:{port}. Please check if LM Studio is running.")
            return ""
        except Exception as e:
            st.error(f"❌ Local LLM error: {str(e)}")
            return ""

###########################################################################

def extract_table_from_llm_response(response, table_name="unknown_table"):
    """
    Enhanced table extraction from LLM response (for AI autofill) with better error handling
    """
    if isinstance(response, str):
        content = response.strip()
        
        # Remove common code block markers
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.lower().startswith("json"):
            content = content[4:].lstrip()
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Try multiple parsing strategies
        parsing_attempts = [
            # 1. Direct JSON parse
            lambda: json.loads(content),
            # 2. Extract JSON object using regex
            lambda: json.loads(re.search(r'\{.*?\}', content, re.DOTALL).group()) if re.search(r'\{.*?\}', content, re.DOTALL) else None,
            # 3. Handle partial response starting with "columns"
            lambda: json.loads('{"name": "' + table_name + '", ' + content + ', "primary_key": ["id"], "foreign_keys": []}') if content.strip().startswith('"columns"') else None,
            # 4. Handle if response is just the columns array
            lambda: {"name": table_name, "columns": json.loads(content), "primary_key": ["id"], "foreign_keys": []} if content.strip().startswith('[') else None,
            # 5. Extract columns array from partial response and wrap
            lambda: {"name": table_name, "columns": json.loads(re.search(r'"columns"\s*:\s*(\[.*?\])', content, re.DOTALL).group(1)), "primary_key": ["id"], "foreign_keys": []} if re.search(r'"columns"\s*:\s*(\[.*?\])', content, re.DOTALL) else None,
            # 6. Handle complete JSON object missing only the "name" field - add it
            lambda: {**json.loads(content), "name": table_name} if content.strip().startswith('{') and '"columns"' in content and '"name"' not in content else None,
            # 7. Clean and retry - fix common JSON issues
            lambda: json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', content))),
            # 8. Fix trailing commas and quotes
            lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', content.replace('"""', '"').replace("'''", "'"))),
            # 9. Try to extract just the table object using more flexible regex
            lambda: json.loads(re.search(r'\{[^{}]*"name"[^{}]*"columns"[^{}]*\[.*?\][^{}]*\}', content, re.DOTALL).group()) if re.search(r'\{[^{}]*"name"[^{}]*"columns"[^{}]*\[.*?\][^{}]*\}', content, re.DOTALL) else None
        ]
        
        for i, attempt in enumerate(parsing_attempts):
            try:
                result = attempt()
                if result is not None:
                    st.success(f"✅ Table JSON parsed using strategy {i+1}")
                    
                    # Normalize foreign_keys format if needed
                    if isinstance(result, dict) and "foreign_keys" in result:
                        normalized_fks = []
                        for fk in result.get("foreign_keys", []):
                            if isinstance(fk, dict):
                                if "from" in fk and "to" in fk:
                                    # Convert {"from": "TableName", "to": "column"} to standard format
                                    normalized_fks.append({
                                        "column": fk["to"],
                                        "references": f"{fk['from']}(id)"
                                    })
                                elif "column" in fk and "references" in fk:
                                    # Already in correct format
                                    normalized_fks.append(fk)
                                else:
                                    # Try to parse other formats
                                    normalized_fks.append(fk)
                        result["foreign_keys"] = normalized_fks
                        st.info(f"🔧 Normalized {len(normalized_fks)} foreign key relationships")
                    
                    response = result
                    break
            except Exception as e:
                st.warning(f"⚠️ Table parse attempt {i+1} failed: {str(e)[:100]}")
                continue
        
        if isinstance(response, str):
            st.error(f"❌ Failed to parse table JSON. Raw content: {content[:300]}...")
            return None

    # If response is a dict and has 'name' and 'columns'
    if isinstance(response, dict):
        # Handle dict keyed by table name
        if len(response) == 1 and isinstance(next(iter(response.values())), dict):
            table_candidate = next(iter(response.values()))
            if "name" in table_candidate and "columns" in table_candidate:
                st.success("✅ Found table structure nested in response")
                return table_candidate
        # Handle direct dict
        if "name" in response and "columns" in response:
            st.success("✅ Found direct table structure in response")
            return response

    # If response is a list with one dict
    if isinstance(response, list) and len(response) == 1 and isinstance(response[0], dict):
        st.success("✅ Found table structure in array format")
        return response[0]

    st.error(f"❌ LLM did not return a valid table structure. Response type: {type(response)}")
    if isinstance(response, dict):
        st.error(f"Available keys: {list(response.keys())}")
    return None
###########################################################################

def extract_questions_from_llm_response(response):
    """
    Enhanced JSON parsing for questions from both Gemini and local LLMs with comprehensive repair
    """
    if isinstance(response, str):
        content = response.strip()
        
        # Remove common code block markers
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.lower().startswith("json"):
            content = content[4:].lstrip()
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Intelligent JSON repair for common truncation issues (same as schema parser)
        original_content = content
        if content:
            # Fix common truncation patterns
            if content.count('"') % 2 != 0:
                st.info("🔧 Attempting to repair truncated JSON string...")
                # If we have an odd number of quotes, likely truncated mid-string
                if content.endswith(','):
                    content = content[:-1]  # Remove trailing comma
                if not content.endswith('"'):
                    content += '"'  # Close the string
            
            # Fix missing closing brackets/braces
            open_brackets = content.count('[') - content.count(']')
            open_braces = content.count('{') - content.count('}')
            
            if open_brackets > 0:
                st.info(f"🔧 Adding {open_brackets} missing closing bracket(s)...")
                content += ']' * open_brackets
                
            if open_braces > 0:
                st.info(f"🔧 Adding {open_braces} missing closing brace(s)...")
                content += '}' * open_braces
            
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            
            if content != original_content:
                st.info(f"🔧 JSON repair applied. Original: {len(original_content)} chars → Repaired: {len(content)} chars")
        
        # Enhanced parsing strategies (similar to schema parser)
        parsing_attempts = [
            # 1. Direct JSON parse - handle both object and array formats
            lambda: json.loads(content),
            # 2. Extract JSON array using regex
            lambda: json.loads(re.search(r'\[.*?\]', content, re.DOTALL).group()) if re.search(r'\[.*?\]', content, re.DOTALL) else None,
            # 3. Extract JSON object with questions key
            lambda: json.loads(re.search(r'\{.*?"questions".*?\}', content, re.DOTALL).group()) if re.search(r'\{.*?"questions".*?\}', content, re.DOTALL) else None,
            # 4. Clean and retry - remove common formatting issues
            lambda: json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', content))),
            # 5. Fix trailing commas and quotes
            lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', content.replace('"""', '"').replace("'''", "'"))),
            # 6. Try to extract just the array part if wrapped in object
            lambda: json.loads('[' + re.search(r'\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*', content, re.DOTALL).group()[1:] + ']') if re.search(r'\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*', content, re.DOTALL) else None,
            # 7. More aggressive cleaning with newline/space normalization
            lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', content.replace('\n', ' ').replace('\r', ' ').replace('"""', '"').replace("'''", "'")))
        ]
        
        for i, attempt in enumerate(parsing_attempts):
            try:
                result = attempt()
                if result is not None:
                    st.success(f"✅ Questions JSON parsed using strategy {i+1}")
                    
                    # Handle different response formats with validation
                    if isinstance(result, dict) and "questions" in result:
                        questions = result["questions"]
                        if isinstance(questions, list) and len(questions) > 0:
                            # Validate questions have required structure
                            valid_questions = [q for q in questions if isinstance(q, dict) and "question" in q and "options" in q]
                            if valid_questions:
                                st.success(f"✅ Found {len(valid_questions)} valid questions in object format!")
                                return valid_questions
                            else:
                                st.warning(f"⚠️ Questions object doesn't contain valid question structures")
                                continue
                    elif isinstance(result, list) and len(result) > 0:
                        # Validate array contains question objects
                        valid_questions = [q for q in result if isinstance(q, dict) and "question" in q and "options" in q]
                        if valid_questions:
                            st.success(f"✅ Found {len(valid_questions)} valid questions in array format!")
                            return valid_questions
                        else:
                            st.warning(f"⚠️ Array doesn't contain valid question objects")
                            continue
                    else:
                        st.warning(f"⚠️ Unexpected result type: {type(result)}")
                        continue
            except Exception as e:
                st.warning(f"⚠️ Questions parse attempt {i+1} failed: {str(e)[:100]}...")
                continue
        
        # If all parsing attempts fail, try to extract questions manually
        st.warning("🔧 Trying manual question extraction...")
        try:
            # Look for question patterns in the text
            question_patterns = [
                r'"question"\s*:\s*"([^"]*\?[^"]*)"',  # Questions with "question": "text?"
                r'"([^"]*\?[^"]*)"',  # Any text in quotes ending with ?
                r'(\d+\.\s*[^?\n]+\?)',  # Numbered questions
            ]
            
            questions = []
            for pattern in question_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if '?' in match and len(match) > 10:  # Basic quality filter
                        questions.append({"question": match, "options": []})
            
            if questions:
                st.success(f"✅ Extracted {len(questions)} questions manually")
                return questions
                
        except Exception as e:
            st.warning(f"Manual question extraction failed: {e}")
        
        # Don't use fallback questions - let the user see the actual error
        st.error("❌ Could not parse questions from LLM response.")
        st.error(f"Raw response: {content[:500]}...")
        return []
    
    # Handle direct dict responses
    if isinstance(response, dict) and "questions" in response:
        questions = response["questions"]
        if isinstance(questions, list):
            return questions
    
    # Handle direct list responses
    if isinstance(response, list):
        return response
    
    st.error("LLM did not return a valid questions array.")
    return []
###########################################################################

def extract_schema_from_llm_response(response):
    """
    Enhanced schema extraction from LLM responses with better error handling
    """
    # If response is a string, try to parse as JSON
    if isinstance(response, str):
        content = response.strip()
        
        # Remove common code block markers
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.lower().startswith("json"):
            content = content[4:].lstrip()
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Intelligent JSON repair for common truncation issues
        original_content = content
        if content:
            # Remove JSON comments (// and /* */) that LLMs sometimes add
            content = re.sub(r'//.*?(?=\n|$)', '', content)  # Remove // comments
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Remove /* */ comments
            
            # CRITICAL: Pre-process to remove foreign_key fields from column definitions
            # This is the root cause of parsing failures - LLMs add foreign_key to columns despite instructions
            content = re.sub(r'[,\s]*"foreign_key"\s*:\s*"[^"]*"', '', content)  # Remove "foreign_key": "value"
            content = re.sub(r'[,\s]*"foreign_key"\s*:\s*\{[^}]*\}', '', content)  # Remove "foreign_key": {...}
            content = re.sub(r'[,\s]*"foreign_key"\s*:\s*\[[^\]]*\]', '', content)  # Remove "foreign_key": [...]
            
            # CRITICAL: Remove "relationships" array that LLMs sometimes add instead of foreign_keys
            content = re.sub(r'[,\s]*"relationships"\s*:\s*\[[^\]]*\]', '', content)  # Remove "relationships": [...]
            
            # CRITICAL: Fix empty column names - replace "" with generic names
            content = re.sub(r'"name"\s*:\s*""', '"name": "column_placeholder"', content)
            
            # Also remove other prohibited column-level fields
            prohibited_column_fields = [
                "primary_key_constraint", "unique_constraint", "index", "nullable", 
                "default", "constraint", "references", "check_constraint"
            ]
            for field in prohibited_column_fields:
                content = re.sub(f'[,\\s]*"{field}"\\s*:\\s*"[^"]*"', '', content)
                content = re.sub(f'[,\\s]*"{field}"\\s*:\\s*\\{{[^}}]*\\}}', '', content)
                content = re.sub(f'[,\\s]*"{field}"\\s*:\\s*\\[[^\\]]*\\]', '', content)
                content = re.sub(f'[,\\s]*"{field}"\\s*:\\s*[^,}}\\]]*', '', content)
            
            # Clean up any resulting formatting issues from field removal
            content = re.sub(r',(\s*,)+', ',', content)  # Remove duplicate commas
            content = re.sub(r'{\s*,', '{', content)  # Remove leading comma in objects
            content = re.sub(r',\s*}', '}', content)  # Remove trailing comma before }
            content = re.sub(r',\s*]', ']', content)  # Remove trailing comma before ]
            
            # Fix common truncation patterns
            if content.count('"') % 2 != 0:
                st.info("🔧 Attempting to repair truncated JSON string...")
                # If we have an odd number of quotes, likely truncated mid-string
                if content.endswith(','):
                    content = content[:-1]  # Remove trailing comma
                if not content.endswith('"'):
                    content += '"'  # Close the string
            
            # Fix missing closing brackets/braces
            open_brackets = content.count('[') - content.count(']')
            open_braces = content.count('{') - content.count('}')
            
            if open_brackets > 0:
                st.info(f"🔧 Adding {open_brackets} missing closing bracket(s)...")
                content += ']' * open_brackets
                
            if open_braces > 0:
                st.info(f"🔧 Adding {open_braces} missing closing brace(s)...")
                content += '}' * open_braces
            
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            
            if content != original_content:
                st.info(f"🔧 JSON repair applied. Original: {len(original_content)} chars → Repaired: {len(content)} chars")
                if "foreign_key" in original_content and "foreign_key" not in content:
                    st.success("✅ Removed prohibited foreign_key fields from column definitions!")
        
        # Try multiple parsing strategies
        parsing_attempts = [
            # 1. Direct JSON parse - handle both object and array formats
            lambda: json.loads(content),
            # 2. If it's an array of tables, wrap it in the expected format
            lambda: {"tables": json.loads(content)} if content.strip().startswith('[') else None,
            # 3. Extract JSON object with tables key using regex (more flexible)
            lambda: json.loads(re.search(r'\{[^{}]*"tables"[^{}]*\[[^\]]*\][^{}]*\}', content, re.DOTALL).group()) if re.search(r'\{[^{}]*"tables"[^{}]*\[[^\]]*\][^{}]*\}', content, re.DOTALL) else None,
            # 4. Try to find and extract the full JSON object
            lambda: json.loads(re.search(r'\{.*?"tables"\s*:\s*\[.*?\]\s*\}', content, re.DOTALL).group()) if re.search(r'\{.*?"tables"\s*:\s*\[.*?\]\s*\}', content, re.DOTALL) else None,
            # 5. Clean common issues and retry
            lambda: json.loads(re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', content.replace('\n', ' ').replace('\r', '')))),
            # 6. Fix trailing commas and quotes
            lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', content.replace('"""', '"').replace("'''", "'").replace('\n', ' '))),
            # 7. Try to parse as array and wrap it (more aggressive cleaning)
            lambda: {"tables": json.loads(re.sub(r',(\s*[}\]])', r'\1', content.replace('"""', '"').replace("'''", "'").replace('\n', ' ')))} if content.strip().startswith('[') else None
        ]
        
        for i, attempt in enumerate(parsing_attempts):
            try:
                result = attempt()
                if result is not None:
                    st.success(f"✅ Schema JSON parsed using strategy {i+1}")
                    
                    # Handle different response formats
                    if isinstance(result, dict) and "tables" in result:
                        # Validate that tables array contains valid table objects
                        tables = result.get("tables", [])
                        if isinstance(tables, list) and len(tables) > 0:
                            valid_tables = all(isinstance(t, dict) and "name" in t and "columns" in t for t in tables)
                            if valid_tables:
                                st.success(f"✅ Found {len(tables)} valid tables in schema!")
                                normalized_result = normalize_schema(result)  # Apply normalization first
                                return auto_detect_foreign_keys(normalized_result)  # Then auto-detect foreign keys
                            else:
                                st.warning(f"⚠️ Schema contains invalid table objects")
                                continue
                        else:
                            st.warning(f"⚠️ Schema tables array is empty or invalid")
                            continue
                    elif isinstance(result, list):
                        # Validate that it's a list of table objects
                        if len(result) > 0 and all(isinstance(t, dict) and "name" in t and "columns" in t for t in result):
                            st.success(f"✅ Parsed array of {len(result)} tables, wrapping in schema format!")
                            normalized_result = normalize_schema({"tables": result})  # Apply normalization first
                            return auto_detect_foreign_keys(normalized_result)  # Then auto-detect foreign keys
                        else:
                            st.warning(f"⚠️ Array doesn't contain valid table objects")
                            continue
                    else:
                        st.warning(f"⚠️ Unexpected result type: {type(result)}")
                        continue
            except Exception as e:
                st.warning(f"⚠️ Schema parse attempt {i+1} failed: {str(e)[:100]}...")
                continue
        
        # If parsing fails, show more details
        st.error(f"Failed to parse schema. Raw response (first 300 chars): {content[:300]}...")
        if len(content) > 300:
            st.error(f"...and {len(content) - 300} more characters")
            
        # Enhanced error detection with specific guidance
        if 'foreign_key' in content:
            st.error("🚨 **CRITICAL ISSUE**: LLM used 'foreign_key' field in column definitions!")
            st.error("💡 **Fix**: Foreign keys should be in 'foreign_keys' array at table level")
            st.error("🔧 **Auto-fix applied**: Removed foreign_key fields from columns during preprocessing")
        if '//' in content:
            st.error("🚨 **Issue Found**: LLM added comments (//) to JSON!")
            st.error("💡 **Fix**: JSON must be pure without comments")
        if '/*' in content:
            st.error("🚨 **Issue Found**: LLM added multi-line comments to JSON!")
            st.error("💡 **Fix**: JSON must be pure without comments")
        
        # Check for other problematic patterns
        problematic_fields = ["primary_key_constraint", "unique_constraint", "index", "nullable", "default"]
        for field in problematic_fields:
            if f'"{field}"' in content:
                st.error(f"🚨 **Issue Found**: LLM added prohibited field '{field}' to columns!")
                st.error(f"💡 **Fix**: Columns should only have: name, type, description")
        
        # Suggest switching LLM if using local model
        llm_source = st.session_state.get("llm_source", "Google Gemini")
        if llm_source != "Google Gemini":
            st.warning("💡 **Recommendation**: Try switching to Google Gemini for more reliable schema generation")
            st.info("**Local LLMs** sometimes struggle with strict JSON formatting requirements")
            
        return {}

    # Handle OpenAI-compatible format
    if isinstance(response, dict) and "choices" in response:
        content = response["choices"][0]["message"]["content"]
        return extract_schema_from_llm_response(content)  # Recursive call

    # Handle direct dict responses
    if isinstance(response, dict) and "tables" in response:
        normalized_result = normalize_schema(response)  # Apply normalization first
        return auto_detect_foreign_keys(normalized_result)  # Then auto-detect foreign keys
    
    # Handle direct list responses (array of tables)
    if isinstance(response, list) and len(response) > 0:
        # Check if it's an array of table objects
        if all(isinstance(item, dict) and "name" in item and "columns" in item for item in response):
            st.success("✅ Detected array of tables, wrapping in proper format!")
            normalized_result = normalize_schema({"tables": response})  # Apply normalization first
            return auto_detect_foreign_keys(normalized_result)  # Then auto-detect foreign keys

    st.error("LLM did not return a valid schema object.")
    return {}
###########################################################################

def normalize_schema(schema):
    """
    Converts columns from 'colname (TYPE)' to {'name': ..., 'type': ...}
    and ensures foreign_keys are dicts. Also extracts foreign_key fields from column definitions.
    Enhanced to handle inconsistent LLM outputs and enforce standard structure.
    """
    if not isinstance(schema, dict) or "tables" not in schema:
        return schema
    
    # Track table names to avoid duplicates
    seen_tables = set()
    normalized_tables = []
    
    for table in schema["tables"]:
        table_name = table.get("name", "unknown")
        
        # Handle duplicate table names
        if table_name in seen_tables:
            st.warning(f"🚨 **Duplicate table detected**: '{table_name}' - skipping duplicate")
            continue
        seen_tables.add(table_name)
        
        # Normalize columns and extract foreign keys from column definitions
        new_columns = []
        extracted_fks = []
        
        for col in table.get("columns", []):
            if isinstance(col, str):
                # Split "colname (TYPE)"
                if "(" in col and col.endswith(")"):
                    name, type_ = col.rsplit("(", 1)
                    new_columns.append({
                        "name": name.strip(),
                        "type": type_[:-1].strip(),  # remove trailing ')'
                        "description": ""
                    })
                else:
                    new_columns.append({"name": col, "type": "", "description": ""})
            elif isinstance(col, dict):
                # Clean column dictionary - remove non-standard fields
                col_copy = {
                    "name": col.get("name", ""),
                    "type": col.get("type", ""),
                    "description": col.get("description", "")
                }
                
                # Remove non-standard fields that LLMs sometimes add
                non_standard_fields = ["primary_key_constraint", "unique_constraint", "index", "nullable", "default"]
                for field in non_standard_fields:
                    if field in col:
                        st.info(f"🔧 Removed non-standard field '{field}' from column '{col.get('name', 'unknown')}'")
                
                # Check if column has a foreign_key field and extract it
                if "foreign_key" in col:
                    fk_ref = col.pop("foreign_key")  # Remove from column definition
                    # Create proper foreign key object
                    extracted_fks.append({
                        "column": col_copy.get("name", ""),
                        "references": fk_ref
                    })
                    st.info(f"🔧 Extracted foreign key: {col_copy.get('name', '')} -> {fk_ref} (moved to proper foreign_keys array)")
                
                # Extract foreign keys from column descriptions
                description = col.get("description", "").lower()
                if "foreign key" in description and "referencing" in description:
                    # Pattern: "Foreign key referencing TableName(column)"
                    import re
                    fk_match = re.search(r'referencing\s+(\w+)\s*\(\s*(\w+)\s*\)', description, re.IGNORECASE)
                    if fk_match:
                        ref_table, ref_column = fk_match.groups()
                        extracted_fks.append({
                            "column": col_copy.get("name", ""),
                            "references": f"{ref_table}({ref_column})"
                        })
                        st.info(f"🔧 Extracted FK from description: {col_copy.get('name', '')} -> {ref_table}({ref_column})")
                
                new_columns.append(col_copy)
        
        table["columns"] = new_columns

        # Normalize foreign_keys and include extracted ones
        new_fks = extracted_fks.copy()  # Start with extracted FKs
        
        for fk in table.get("foreign_keys", []):
            if isinstance(fk, dict):
                # Handle non-standard foreign key formats from LLMs
                if "constraint" in fk and "FOREIGN KEY" in fk.get("constraint", ""):
                    # Parse: "FOREIGN KEY(references:tablename(column))"
                    constraint = fk["constraint"]
                    import re
                    fk_match = re.search(r'references:\s*(\w+)\s*\(\s*(\w+)\s*\)', constraint, re.IGNORECASE)
                    if fk_match:
                        ref_table, ref_column = fk_match.groups()
                        new_fks.append({
                            "column": fk.get("column", ""),
                            "references": f"{ref_table.title()}({ref_column})"
                        })
                        st.info(f"🔧 Normalized non-standard FK: {fk.get('column', '')} -> {ref_table.title()}({ref_column})")
                    else:
                        st.warning(f"⚠️ Could not parse foreign key constraint: {constraint}")
                elif "references" in fk:
                    # Standard format - keep as is
                    new_fks.append(fk)
                else:
                    st.warning(f"⚠️ Unknown foreign key format: {fk}")
            elif isinstance(fk, str):
                # Try to parse "column -> references"
                parts = fk.split("->")
                if len(parts) == 2:
                    new_fks.append({"column": parts[0].strip(), "references": parts[1].strip()})
                elif ":" in fk:
                    # Try "column:references"
                    col, ref = fk.split(":", 1)
                    new_fks.append({"column": col.strip(), "references": ref.strip()})
        
        table["foreign_keys"] = new_fks
        
        # Ensure table always has required fields with proper defaults
        if "primary_key" not in table or not table["primary_key"]:
            table["primary_key"] = ["id"]  # Default primary key
        if "foreign_keys" not in table:
            table["foreign_keys"] = []  # Ensure empty array if missing
        
        # Remove non-standard table-level fields that LLMs sometimes add
        table_non_standard = ["unique_constraints", "indexes", "constraints", "triggers"]
        for field in table_non_standard:
            if field in table:
                st.info(f"🔧 Removed non-standard table field '{field}' from table '{table_name}'")
                del table[field]
        
        normalized_tables.append(table)
    
    # Update schema with normalized tables
    schema["tables"] = normalized_tables
    
    # Show summary of normalization
    if len(normalized_tables) != len(schema.get("tables", [])):
        st.success(f"✅ Schema normalized: {len(normalized_tables)} tables (removed {len(schema.get('tables', [])) - len(normalized_tables)} duplicates)")
    else:
        st.success(f"✅ Schema normalized: {len(normalized_tables)} tables processed")
    
    return schema

###########################################################################

def auto_detect_foreign_keys(schema):
    """
    Automatically detect and create foreign key relationships based on naming patterns
    and table structures when LLM fails to create them properly.
    """
    if not isinstance(schema, dict) or "tables" not in schema:
        return schema
    
    tables = schema["tables"]
    table_names = [table.get("name", "") for table in tables]
    
    # Create a mapping of potential foreign key patterns
    detected_fks = []
    
    for table in tables:
        table_name = table.get("name", "")
        existing_fks = {fk.get("column", ""): fk.get("references", "") for fk in table.get("foreign_keys", [])}
        new_fks = []
        
        for column in table.get("columns", []):
            col_name = column.get("name", "").lower()
            col_type = column.get("type", "").upper()
            
            # Skip if already has foreign key defined
            if col_name in existing_fks:
                continue
            
            # Only process INT columns that could be foreign keys
            if "INT" not in col_type:
                continue
            
            # Pattern 1: Direct table name + _id (e.g., user_id -> Users)
            if col_name.endswith("_id"):
                base_name = col_name[:-3]  # Remove "_id"
                
                # Look for matching table names (case insensitive, with pluralization)
                possible_tables = []
                for target_table in table_names:
                    target_lower = target_table.lower()
                    
                    # Exact match (e.g., user_id -> User)
                    if target_lower == base_name:
                        possible_tables.append(target_table)
                    # Plural match (e.g., user_id -> Users)
                    elif target_lower == base_name + "s":
                        possible_tables.append(target_table)
                    # Singular match (e.g., users_id -> Users)
                    elif target_lower == base_name[:-1] and base_name.endswith("s"):
                        possible_tables.append(target_table)
                    # Partial match for compound names (e.g., author_id -> Project2025Moderators if it contains "author")
                    elif base_name in target_lower or any(word in target_lower for word in base_name.split("_")):
                        possible_tables.append(target_table)
                
                if possible_tables:
                    # Use the first match (could be enhanced with better logic)
                    target_table = possible_tables[0]
                    new_fks.append({
                        "column": column.get("name", ""),
                        "references": f"{target_table}(id)"
                    })
                    detected_fks.append(f"{table_name}.{col_name} -> {target_table}(id)")
            
            # Pattern 2: Column name matches table name (e.g., comment_id in PositiveRecommendation -> Project2025Comments)
            elif any(table_part.lower() in col_name for table_part in table_names 
                    for table_part in [table_part.lower().replace("2025", "").replace("project", "")]):
                for target_table in table_names:
                    clean_target = target_table.lower().replace("2025", "").replace("project", "")
                    if clean_target in col_name or col_name in clean_target:
                        if target_table != table_name:  # Don't self-reference
                            new_fks.append({
                                "column": column.get("name", ""),
                                "references": f"{target_table}(id)"
                            })
                            detected_fks.append(f"{table_name}.{col_name} -> {target_table}(id)")
                            break
        
        # Add detected foreign keys to existing ones
        table["foreign_keys"] = table.get("foreign_keys", []) + new_fks
    
    # Report what was detected
    if detected_fks:
        st.success(f"🔗 **Auto-detected {len(detected_fks)} foreign key relationships:**")
        for fk in detected_fks:
            st.info(f"   • {fk}")
    
    return schema

###########################################################################

def call_gemini(user_intent):
    llm_source = st.session_state.get("llm_source", "Google Gemini")
    
    if llm_source == "Google Gemini":
        # Sophisticated prompt for Gemini with domain analysis
        prompt = f"""You are a senior data architect and domain expert specializing in "{user_intent}". 

TASK: Analyze the user's intent and generate exactly 3 sophisticated clarifying questions that will help design the perfect database schema.

USER INTENT: "{user_intent}"

ANALYSIS FRAMEWORK:
1. **Business Context**: What are the core business processes, stakeholders, and workflows?
2. **Data Relationships**: What entities interact and how? What are the key relationships?
3. **Scale & Complexity**: What volume, frequency, and complexity of data operations?
4. **Use Cases**: What analytical, operational, and reporting needs exist?

GENERATE 3 STRATEGIC QUESTIONS covering:
- **Scope & Scale**: Business size, data volume, time horizons, geographic scope
- **Core Entities**: Primary business objects, their relationships, and hierarchies  
- **Use Cases**: Key workflows, analytics needs, compliance requirements

Each question should have 4-6 nuanced options that reflect real-world scenarios in the "{user_intent}" domain.

OUTPUT FORMAT: JSON array with this exact structure:
[
  {{"type": "multiple_choice", "question": "What is the primary scale and scope of your {user_intent.lower()} operations?", "options": ["Small-scale local operations (hundreds of records)", "Regional business with moderate complexity (thousands of records)", "Enterprise-level with complex workflows (tens of thousands of records)", "Large-scale distributed operations (hundreds of thousands+ records)"]}},
  {{"type": "multiple_choice", "question": "Which core entities and relationships are most critical to your {user_intent.lower()} system?", "options": ["Basic entity management with simple relationships", "Moderate complexity with hierarchical structures", "Complex multi-entity relationships with dependencies", "Enterprise-grade with advanced business rules"]}},
  {{"type": "multiple_choice", "question": "What are your primary use cases and analytical requirements?", "options": ["Basic CRUD operations and simple reporting", "Operational workflows with standard analytics", "Advanced analytics and business intelligence", "Real-time processing and predictive analytics"]}}
]

DOMAIN EXPERTISE: Apply deep knowledge of {user_intent} industry standards, best practices, and common business patterns. Make questions specific to this domain's unique characteristics and challenges."""
        
    else:
        # Enhanced prompt for Local LLM with domain-specific intelligence
        prompt = f"""You are a senior database architect and domain expert in "{user_intent}".

OBJECTIVE: Create 3 strategic clarifying questions to design the optimal database schema.

USER INTENT: "{user_intent}"

DOMAIN ANALYSIS:
- What are the core business entities in {user_intent}?
- What relationships and workflows exist?
- What scale and complexity is typical?
- What are the key business rules and constraints?

REQUIRED: Generate 3 sophisticated questions covering:

1. **BUSINESS SCOPE & SCALE**
   - Operations size and geographic reach
   - Data volume and growth expectations
   - Time horizons and historical requirements

2. **CORE ENTITIES & RELATIONSHIPS** 
   - Primary business objects and their interactions
   - Hierarchies, dependencies, and business rules
   - Regulatory or compliance considerations

3. **USE CASES & ANALYTICS**
   - Operational workflows and processes
   - Reporting and analytics requirements
   - Performance and scalability needs

CRITICAL: Questions must be specific to "{user_intent}" domain with realistic, nuanced options.

JSON OUTPUT:
[
  {{"type": "multiple_choice", "question": "What is the operational scale of your {user_intent.lower()} system?", "options": ["Small business operations", "Regional enterprise", "Large-scale distributed", "Global enterprise"]}},
  {{"type": "multiple_choice", "question": "Which entities are central to your {user_intent.lower()} workflows?", "options": ["Basic core entities", "Moderate complexity", "Complex relationships", "Enterprise architecture"]}},
  {{"type": "multiple_choice", "question": "What are your primary analytical and operational needs?", "options": ["Basic operations", "Standard analytics", "Advanced BI", "Real-time processing"]}}
]"""
    
    response_text = call_llm(prompt, mode="questions")
    
    # Check if we got an empty response (API error)
    if not response_text or response_text.strip() == "":
        st.error("❌ No response received from LLM. Check your API configuration.")
        return []
    
    questions = extract_questions_from_llm_response(response_text)
    
    # Handle both Gemini and local LLM structure
    if isinstance(questions, dict) and "questions" in questions:
        questions = questions["questions"]
    
    # Filter out questions without options (descriptive types) and limit to exactly 3
    if isinstance(questions, list):
        valid_questions = []
        for q in questions:
            if isinstance(q, dict) and q.get("options") and len(q.get("options", [])) > 0:
                valid_questions.append(q)
        
        if len(valid_questions) >= 3:
            return valid_questions[:3]  # Return exactly 3 valid questions
        elif len(valid_questions) > 0:
            return valid_questions  # Return what we have if less than 3 but more than 0
    
    st.error("LLM did not return valid multiple-choice questions.")
    return []

###########################################################################

def call_gemini_schema(user_intent, answers):
    llm_source = st.session_state.get("llm_source", "Google Gemini")
    
    if llm_source == "Google Gemini":
        # Simplified, focused prompt for Gemini
        context_analysis = ""
        for question, answer in answers.items():
            context_analysis += f"- {question}: {answer}\n"
            
        prompt = f"""Create a database schema for {user_intent}.

User Requirements:
{context_analysis}

CREATE EXACTLY 5-7 TABLES with meaningful relationships and business logic.

ABSOLUTE MANDATORY JSON STRUCTURE - NO DEVIATIONS ALLOWED:

{{
  "tables": [
    {{
      "name": "MainEntityTable",
      "columns": [
        {{"name": "id", "type": "INT", "description": "Primary key"}},
        {{"name": "entity_specific_field", "type": "VARCHAR(255)", "description": "Field relevant to your domain"}},
        {{"name": "another_field", "type": "VARCHAR(100)", "description": "Another domain field"}},
        {{"name": "created_at", "type": "TIMESTAMP", "description": "Creation timestamp"}}
      ],
      "primary_key": ["id"],
      "foreign_keys": []
    }},
    {{
      "name": "RelatedTable",
      "columns": [
        {{"name": "id", "type": "INT", "description": "Primary key"}},
        {{"name": "main_entity_id", "type": "INT", "description": "Foreign key to MainEntityTable"}},
        {{"name": "related_field", "type": "VARCHAR(255)", "description": "Field specific to this table"}},
        {{"name": "status", "type": "VARCHAR(50)", "description": "Status field"}}
      ],
      "primary_key": ["id"],
      "foreign_keys": [
        {{"column": "main_entity_id", "references": "MainEntityTable(id)"}}
      ]
    }},
    {{
      "name": "CategoryTable", 
      "columns": [
        {{"name": "id", "type": "INT", "description": "Primary key"}},
        {{"name": "name", "type": "VARCHAR(255)", "description": "Category name"}},
        {{"name": "description", "type": "TEXT", "description": "Category description"}}
      ],
      "primary_key": ["id"],
      "foreign_keys": []
    }}
  ]
}}

📋 TEMPLATE EXPLANATION:
The above is just a TEMPLATE showing the JSON structure.
Replace "MainEntityTable", "RelatedTable", "CategoryTable" with actual table names for {user_intent}.
Replace "entity_specific_field", "related_field" with actual column names for your domain.

� RELATIONAL CONNECTION PATTERN:
Notice how the example shows a fully connected schema:
- Customers → Orders (via customer_id)
- Orders → OrderItems (via order_id)  
- Products → OrderItems (via product_id)
- Categories → Products (via category_id)
Every table connects to create a complete relational network!

�🚨 CRITICAL REQUIREMENTS:
1. CREATE EXACTLY 5-7 TABLES (NOT JUST ONE!) - Multiple tables are mandatory
2. ALL TABLES MUST BE CONNECTED - Every table must relate to at least one other table via foreign keys
3. EVERY column MUST have a "name" field with actual column name (NEVER empty string)
4. EVERY column MUST have a "type" field (INT, VARCHAR(255), DECIMAL(10,2), TIMESTAMP, BOOLEAN)
5. EVERY column MUST have a "description" field
6. NO "relationships" array - USE foreign_keys array ONLY
7. Foreign keys format: {{"column": "field_name", "references": "TableName(id)"}}
8. CREATE A CONNECTED SCHEMA - No isolated tables allowed

RELATIONAL DESIGN RULES:
- Create tables specific to {user_intent} domain (NOT generic customers/orders!)
- Start with core entities relevant to your domain
- Add supporting tables specific to your use case  
- Connect everything with foreign keys
- Use "_id" suffix for foreign key columns
- Think about what entities exist in {user_intent}

FORBIDDEN FIELDS:
- "foreign_key" in columns
- "relationships" array
- Any field other than: name, columns, primary_key, foreign_keys

COLUMN NAMING RULES:
- Primary key: "id"
- Foreign keys: "table_name_id" (e.g., "customer_id", "order_id")
- Regular fields: descriptive names (e.g., "email", "first_name", "total_amount")

MANDATORY: Your response MUST contain 5-7 CONNECTED tables in the "tables" array.
Return ONLY valid JSON with the exact structure shown above.

🚨 CRITICAL: Replace "MainEntityTable", "RelatedTable" with actual table names for {user_intent}!
DO NOT copy the template literally - create domain-specific tables!"""

    else:
        # Simplified prompt for Local LLM
        context_info = ""
        for question, answer in answers.items():
            context_info += f"- {question}: {answer}\n"
        
        prompt = f"""Create database schema for {user_intent}.

Requirements:
{context_info}

CREATE EXACTLY 5-7 TABLES - DO NOT CREATE JUST ONE TABLE!

ABSOLUTE MANDATORY JSON STRUCTURE - ZERO TOLERANCE FOR DEVIATIONS:

{{
  "tables": [
    {{
      "name": "MainEntityTable",
      "columns": [
        {{"name": "id", "type": "INT", "description": "Primary key"}},
        {{"name": "domain_field", "type": "VARCHAR(255)", "description": "Field specific to {user_intent}"}},
        {{"name": "another_field", "type": "VARCHAR(100)", "description": "Another relevant field"}},
        {{"name": "created_at", "type": "TIMESTAMP", "description": "Creation date"}}
      ],
      "primary_key": ["id"],
      "foreign_keys": []
    }},
    {{
      "name": "RelatedTable",
      "columns": [
        {{"name": "id", "type": "INT", "description": "Primary key"}},
        {{"name": "main_entity_id", "type": "INT", "description": "Foreign key to MainEntityTable"}},
        {{"name": "related_field", "type": "VARCHAR(255)", "description": "Field for this table"}},
        {{"name": "status", "type": "VARCHAR(50)", "description": "Status field"}}
      ],
      "primary_key": ["id"],
      "foreign_keys": [
        {{"column": "main_entity_id", "references": "MainEntityTable(id)"}}
      ]
    }}
  ]
}}

📋 TEMPLATE EXPLANATION:
This is just a TEMPLATE. Replace table names and column names with ones specific to {user_intent}.

📋 CONNECTION PATTERN SHOWN ABOVE:
- MainEntityTable connects to RelatedTable  
- Use actual table names for {user_intent}, not these template names!
Create domain-specific tables!

CRITICAL VALIDATION RULES:
1. CREATE EXACTLY 5-7 TABLES (NOT JUST ONE!) - Multiple tables are mandatory
2. ALL TABLES MUST CONNECT - Every table needs foreign keys to other tables
3. EVERY column "name" MUST be filled (NEVER empty string "")
4. EVERY column "type" MUST be specified (INT, VARCHAR(255), DECIMAL(10,2), TIMESTAMP, BOOLEAN)
5. EVERY column "description" MUST be meaningful
6. NO "relationships" array anywhere
7. ONLY "foreign_keys" array for relationships

SIMPLE CONNECTION RULES:
- Create core tables specific to {user_intent}
- Add support tables relevant to your domain
- Connect with foreign keys using domain-appropriate names
- Every table should link to at least one other table
- DO NOT use generic "Customers", "Products" unless actually relevant!

COLUMN NAMING MANDATORY PATTERNS:
- Primary key: "id" 
- Foreign keys: "table_name_id" (customer_id, order_id, product_id)
- Regular columns: actual field names (email, first_name, price, status)

ABSOLUTELY FORBIDDEN:
- Empty column names: {{"name": "", ...}}
- Missing types: {{"type": "", ...}}
- "relationships" array
- Any structure deviation
- Creating only one table when 5-7 are required
- Isolated tables with no foreign keys

MANDATORY: Your JSON must contain 5-7 CONNECTED tables in the "tables" array.
Return EXACTLY the JSON structure shown above with actual column names filled in.

🚨 CRITICAL: Replace "MainEntityTable", "RelatedTable" with actual table names for {user_intent}!
DO NOT copy the template literally - create domain-specific tables!"""

    response = call_llm(prompt, mode="schema")
    
    # Add debug info for schema generation
    if not response or response.strip() == "":
        st.error("❌ Empty response from LLM during schema generation")
        if llm_source != "Google Gemini":
            st.info("💡 **Local LLM troubleshooting:**")
            st.info("• The prompt might be too complex - try Google Gemini instead")
            st.info("• Check LM Studio model settings and performance")
            st.info("• Ensure model has enough context length for schema generation")
        return {}
    
    st.info(f"📝 Received schema response ({len(response)} chars)")
    schema = extract_schema_from_llm_response(response)
    if isinstance(schema, dict) and "tables" in schema:
        return schema
    st.error("LLM did not return a valid schema.")
    return {}

###########################################################################

def render_er(schema):
    dot = graphviz.Digraph()
    dot.attr(rankdir='TB')
    tables = schema.get("tables", [])
    
    for table in tables:
        # Build table label with proper HTML-like formatting
        label_parts = [f"<b>{table['name']}</b>"]
        for col in table.get("columns", []):
            col_name = col.get('name', 'unknown')
            col_type = col.get('type', 'unknown')
            # Escape special characters and build label
            label_parts.append(f"{col_name} : {col_type}")
        
        # Join with line breaks and wrap in HTML-like label
        label = "<<table border='0' cellborder='1' cellspacing='0'>"
        label += f"<tr><td bgcolor='lightblue'><b>{table['name']}</b></td></tr>"
        for col in table.get("columns", []):
            col_name = col.get('name', 'unknown')
            col_type = col.get('type', 'unknown')
            pk_indicator = " 🔑" if col_name in table.get("primary_key", []) else ""
            label += f"<tr><td align='left'>{col_name} : {col_type}{pk_indicator}</td></tr>"
        label += "</table>>"
        
        dot.node(table["name"], label=label, shape="plaintext")
    
    # Add edges for foreign key relationships
    for table in tables:
        for fk in table.get("foreign_keys", []):
            if fk.get("references"):
                # Extract referenced table name from "TableName(column)" format
                ref_full = fk["references"]
                if "(" in ref_full:
                    ref_table = ref_full.split("(")[0].strip()
                else:
                    ref_table = ref_full.strip()
                
                # Add edge with foreign key label
                dot.edge(table["name"], ref_table, label=fk.get("column", ""), color="blue")
    
    return dot

###########################################################################

def ai_estimate_row_counts(schema, user_intent, user_answers):
    """
    AI-powered estimation of appropriate row counts for each table based on business context
    """
    llm_source = st.session_state.get("llm_source", "Google Gemini")
    tables = schema.get("tables", [])
    
    if not tables:
        return {}
    
    # Build context about the schema and user requirements
    context_info = f"User Intent: {user_intent}\n"
    if user_answers:
        context_info += "User Requirements:\n"
        for question, answer in user_answers.items():
            context_info += f"- {question}: {answer}\n"
    
    # Create table summary for the prompt
    table_summary = []
    for table in tables:
        table_info = f"- {table.get('name', 'unknown')}: "
        columns = table.get('columns', [])
        if columns:
            col_names = [col.get('name', 'unknown') for col in columns[:3]]  # First 3 columns
            table_info += f"columns include {', '.join(col_names)}"
            if len(columns) > 3:
                table_info += f" and {len(columns)-3} more"
        table_summary.append(table_info)
    
    if llm_source == "Google Gemini":
        prompt = f"""You are a data analyst and database expert. Analyze this database schema and estimate realistic row counts for each table.

CONTEXT:
{context_info}

SCHEMA TABLES:
{chr(10).join(table_summary)}

TASK: For each table, estimate a realistic number of rows and provide a brief business justification.

Consider these factors:
- Master data tables (categories, products, users) typically have fewer rows
- Transaction tables (orders, payments, logs) typically have many more rows  
- Reference/lookup tables usually have very few rows (5-50)
- Business volume and scale based on user requirements
- Realistic business ratios (e.g., users vs orders vs order items)

RETURN FORMAT: Valid JSON object with this exact structure:
{{
  "table_name": {{
    "estimated_rows": 1000,
    "justification": "Brief business reason for this estimate"
  }},
  "another_table": {{
    "estimated_rows": 50,
    "justification": "Another brief business reason"
  }}
}}

Return ONLY the JSON object, no explanations."""

    else:
        # Simplified prompt for local LLM
        prompt = f"""Estimate row counts for database tables.

Context: {user_intent}

Tables: {', '.join([t.get('name', 'unknown') for t in tables])}

Return JSON:
{{
  "table_name": {{"estimated_rows": 100, "justification": "Brief reason"}},
  "table2": {{"estimated_rows": 1000, "justification": "Brief reason"}}
}}

Consider:
- Master data: 50-500 rows
- Transactions: 1000+ rows
- Categories: 5-50 rows"""

    response = call_llm(prompt, mode="estimation")
    
    if not response or response.strip() == "":
        st.warning("❌ Could not get AI row count estimates. Using defaults.")
        return generate_default_row_counts(tables)
    
    try:
        estimates = extract_row_estimates_from_response(response)
        if estimates:
            st.success(f"✅ AI estimated row counts for {len(estimates)} tables")
            return estimates
        else:
            st.warning("⚠️ Could not parse AI estimates. Using defaults.")
            return generate_default_row_counts(tables)
    except Exception as e:
        st.warning(f"⚠️ Error parsing estimates: {str(e)}. Using defaults.")
        return generate_default_row_counts(tables)

def extract_row_estimates_from_response(response):
    """
    Extract row count estimates from LLM response
    """
    if isinstance(response, str):
        content = response.strip()
        
        # Remove code block markers
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            # Try direct JSON parse
            result = json.loads(content)
            if isinstance(result, dict):
                # Validate structure
                valid_estimates = {}
                for table_name, estimate_data in result.items():
                    if isinstance(estimate_data, dict) and "estimated_rows" in estimate_data:
                        valid_estimates[table_name] = estimate_data
                    elif isinstance(estimate_data, int):
                        # Handle simple format: {"table": 100}
                        valid_estimates[table_name] = {
                            "estimated_rows": estimate_data,
                            "justification": "AI estimate based on table characteristics"
                        }
                return valid_estimates
        except:
            pass
        
        # Try regex extraction as fallback
        try:
            # Look for patterns like "table_name": {"estimated_rows": 100, "justification": "..."}
            table_patterns = re.findall(r'"([^"]+)":\s*\{\s*"estimated_rows":\s*(\d+),\s*"justification":\s*"([^"]*)"', content)
            if table_patterns:
                estimates = {}
                for table_name, rows, justification in table_patterns:
                    estimates[table_name] = {
                        "estimated_rows": int(rows),
                        "justification": justification
                    }
                return estimates
        except:
            pass
    
    return {}

def generate_default_row_counts(tables):
    """
    Generate sensible default row counts based on table names and characteristics
    """
    defaults = {}
    
    for table in tables:
        table_name = table.get("name", "").lower()
        
        # Heuristics based on common table naming patterns
        if any(keyword in table_name for keyword in ["category", "categories", "type", "status", "role"]):
            # Reference/lookup tables
            row_count = 15
            justification = "Reference table - typically contains a small set of predefined values"
        elif any(keyword in table_name for keyword in ["user", "customer", "client", "member", "person"]):
            # User tables
            row_count = 250
            justification = "User table - moderate number of users for a typical application"
        elif any(keyword in table_name for keyword in ["product", "item", "service", "inventory"]):
            # Product/inventory tables
            row_count = 150
            justification = "Product catalog - typical e-commerce or service inventory size"
        elif any(keyword in table_name for keyword in ["order", "transaction", "payment", "purchase", "sale"]):
            # Transaction tables
            row_count = 2000
            justification = "Transaction table - high volume operational data"
        elif any(keyword in table_name for keyword in ["log", "audit", "event", "activity", "history"]):
            # Log/audit tables
            row_count = 5000
            justification = "Log table - contains historical activity and audit trails"
        elif any(keyword in table_name for keyword in ["detail", "item", "line"]):
            # Detail/line item tables
            row_count = 3000
            justification = "Detail table - multiple items per main entity (orders, etc.)"
        else:
            # Generic entity table
            row_count = 500
            justification = "Standard entity table - balanced dataset for typical business operations"
        
        defaults[table.get("name", "unknown")] = {
            "estimated_rows": row_count,
            "justification": justification
        }
    
    return defaults

###########################################################################

def render_agraph(schema):
    tables = schema.get("tables", [])
    nodes = []
    edges = []
    
    # Create nodes for each table
    for table in tables:
        # Count columns for node size
        num_columns = len(table.get("columns", []))
        node_size = max(40, min(80, 30 + num_columns * 3))  # Scale size based on columns
        
        nodes.append(Node(
            id=table["name"],
            label=table["name"],
            size=node_size,
            color="#667eea",
            shape="box",
            title=f"Table: {table['name']}\nColumns: {num_columns}"  # Tooltip
        ))
    
    # Create edges for foreign key relationships
    for table in tables:
        table_name = table["name"]
        for fk in table.get("foreign_keys", []):
            if fk.get("references") and fk.get("column"):
                ref_full = fk["references"]
                fk_column = fk["column"]
                
                # Extract referenced table name from various formats
                if "(" in ref_full and ref_full.endswith(")"):
                    # Format: "TableName(column_name)"
                    ref_table = ref_full.split("(")[0].strip()
                elif "." in ref_full:
                    # Format: "TableName.column_name"
                    ref_table = ref_full.split(".")[0].strip()
                else:
                    # Just table name
                    ref_table = ref_full.strip()
                
                # Only add edge if referenced table exists
                if any(t["name"] == ref_table for t in tables):
                    edges.append(Edge(
                        source=table_name, 
                        target=ref_table, 
                        label=fk_column,
                        color="#f87171",
                        width=2
                    ))
    
    config = Config(
        width=1100, 
        height=650,
        directed=True,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=True,
        node={
            'color': "#667eea", 
            'size': 50, 
            'fontColor': 'white', 
            'fontSize': 14,
            'fontWeight': 'bold'
        },
        link={
            'color': "#f87171", 
            'labelProperty': 'label', 
            'fontColor': '#333',
            'fontSize': 12
        }
    )
    return agraph(nodes=nodes, edges=edges, config=config)

###########################################################################

def ai_autofill_table(schema, new_table_name):
    """
    AI-powered table structure generation based on existing schema context
    """
    llm_source = st.session_state.get("llm_source", "Google Gemini")
    existing_tables = schema.get("tables", [])
    table_names = [t.get("name", "") for t in existing_tables if isinstance(t, dict)]
    
    # Analyze existing schema to understand the domain with much better context
    domain_context = "Unknown Domain"
    business_context = ""
    
    if table_names:
        domain_indicators = []
        for name in table_names:
            domain_indicators.extend(name.lower().split('_'))
        domain_context = f"Domain appears to be related to: {', '.join(set(domain_indicators))}"
        
        # Build comprehensive business context from existing tables
        business_context = "EXISTING SCHEMA CONTEXT:\n"
        for table in existing_tables[:5]:  # Show more tables for better context
            table_name = table.get('name', 'unknown')
            columns = table.get('columns', [])
            col_info = [f"{col.get('name', 'unknown')}({col.get('type', 'unknown')})" for col in columns[:4]]
            business_context += f"• {table_name}: {', '.join(col_info)}\n"
        
        # Infer business domain from table structure
        if any('project' in name.lower() for name in table_names):
            domain_context = "Project Management System"
        elif any('order' in name.lower() or 'payment' in name.lower() for name in table_names):
            domain_context = "E-commerce/Sales System"
        elif any('user' in name.lower() or 'customer' in name.lower() for name in table_names):
            domain_context = "Customer Management System"
    
    if llm_source == "Google Gemini":
        # Sophisticated domain-aware prompt for Gemini with better context
        prompt = f"""You are a senior database architect analyzing an existing schema to design a new table.

EXISTING SCHEMA ANALYSIS:
{domain_context}

CURRENT TABLES: {', '.join(table_names) if table_names else 'None (this is the first table)'}

{business_context}

NEW TABLE REQUEST: "{new_table_name}"

CRITICAL ANALYSIS:
Based on the existing schema, this appears to be a {domain_context} database. The new table "{new_table_name}" should be designed to fit seamlessly into this domain with appropriate business logic and relationships.

DESIGN MISSION:
Create a sophisticated, production-ready table structure for "{new_table_name}" that:

1. **DOMAIN ALIGNMENT**: Perfectly matches the {domain_context} business domain
2. **SCHEMA INTEGRATION**: Connects meaningfully to existing tables: {', '.join(table_names[:3]) if table_names else 'none'}
3. **BUSINESS LOGIC**: Reflects real-world operations in this specific domain
4. **RELATIONSHIP MAPPING**: Include foreign keys to relevant existing tables

TABLE SPECIFICATIONS FOR "{new_table_name}":
- **Business Purpose**: What role does this table serve in {domain_context}?
- **Columns**: 5-8 domain-specific fields (avoid generic name/description)
- **Data Types**: Use INT, BIGINT, VARCHAR(255), DECIMAL(10,2), TIMESTAMP, BOOLEAN appropriately
- **Relationships**: Foreign keys to {', '.join(table_names[:3]) if table_names else 'none'} where logical
- **Domain Fields**: Include industry-specific identifiers, codes, status fields

SPECIFIC GUIDANCE FOR "{new_table_name}":
Consider what "{new_table_name}" represents in a {domain_context} context and design columns that reflect that business reality.

CRITICAL JSON FORMAT (respond with ONLY this JSON, no extra fields):
{{
  "name": "{new_table_name}",
  "columns": [
    {{"name": "id", "type": "BIGINT", "description": "Primary key identifier"}},
    {{"name": "domain_specific_field", "type": "VARCHAR(255)", "description": "Field specific to {domain_context}"}},
    {{"name": "another_business_field", "type": "VARCHAR(100)", "description": "Another domain-relevant field"}},
    {{"name": "status", "type": "VARCHAR(50)", "description": "Current status or state"}},
    {{"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"}},
    {{"name": "updated_at", "type": "TIMESTAMP", "description": "Last modification timestamp"}}
  ],
  "primary_key": ["id"],
  "foreign_keys": [
    {{"column": "related_entity_id", "references": "ExistingTable(id)"}}
  ]
}}

CRITICAL CONSTRAINTS:
- Columns must have ONLY: name, type, description (no primary_key_constraint, nullable, etc.)
- Tables must have ONLY: name, columns, primary_key, foreign_keys (no indexes, constraints, etc.)
- Foreign keys format: {{"column": "field_name", "references": "TableName(id)"}}
- Use standard data types: INT, BIGINT, VARCHAR(255), DECIMAL(10,2), TIMESTAMP, BOOLEAN"""

    else:
        # Enhanced domain-aware prompt for Local LLM with better context
        prompt = f"""TASK: Design table "{new_table_name}" for {domain_context}

{business_context}

DOMAIN CONTEXT: {domain_context}
NEW TABLE: "{new_table_name}"

REQUIREMENTS:
1. Create 5-7 columns specific to {domain_context} domain
2. Make "{new_table_name}" fit logically into existing schema
3. Use appropriate data types: INT, VARCHAR(255), DECIMAL(10,2), TIMESTAMP, BOOLEAN
4. Include foreign keys to existing tables: {', '.join(table_names[:3]) if table_names else 'none'}
5. Avoid generic name/description fields - be domain-specific

BUSINESS LOGIC:
What does "{new_table_name}" represent in a {domain_context}? Design columns that reflect that specific business purpose.

EXAMPLE FOR {domain_context}:
If this is project management, think about project phases, client industries, sectors, etc.
If this is e-commerce, think about product categories, customer segments, etc.

JSON OUTPUT (EXACT FORMAT REQUIRED):
{{
  "name": "{new_table_name}",
  "columns": [
    {{"name": "id", "type": "BIGINT", "description": "Primary identifier"}},
    {{"name": "domain_specific_field", "type": "VARCHAR(255)", "description": "Field relevant to {domain_context}"}},
    {{"name": "code_or_identifier", "type": "VARCHAR(50)", "description": "Business code or identifier"}},
    {{"name": "status", "type": "VARCHAR(50)", "description": "Current status"}},
    {{"name": "created_at", "type": "TIMESTAMP", "description": "Creation time"}}
  ],
  "primary_key": ["id"],
  "foreign_keys": [
    {{"column": "related_id", "references": "ExistingTable(id)"}}
  ]
}}

CRITICAL: 
- Columns must have ONLY: name, type, description
- Tables must have ONLY: name, columns, primary_key, foreign_keys
- NO extra fields like: indexes, constraints, primary_key_constraint, nullable, etc.
- Foreign keys format: {{"column": "field_name", "references": "TableName(id)"}}"""

    response = call_llm(prompt, mode="autofill")
    
    # Add debug information with better analysis
    if response:
        st.info(f"🔍 **AI Response for '{new_table_name}' table:**")
        st.info(f"Response length: {len(response)} characters")
        
        # Check for specific issues
        if 'generic' in response.lower() or 'example' in response.lower():
            st.warning("⚠️ **Detected generic response** - AI may not understand domain context")
        if len(response) < 100:
            st.warning("⚠️ **Very short response** - AI may have failed to generate full structure")
        if '```' in response:
            st.info("✅ Response contains code blocks - likely properly formatted")
        if 'foreign_key' in response and '"foreign_key"' in response:
            st.warning("🚨 **Found inline foreign_key** - will need to extract and normalize")
        
        # Show partial response for debugging
        if len(response) > 300:
            st.info(f"First 300 chars: {response[:300]}...")
        else:
            st.info(f"Full response: {response}")
    else:
        st.error("❌ **No response received from AI** - check LLM connection and configuration")
        return None  # Return None to trigger immediate fallback
    
    table = extract_table_from_llm_response(response, new_table_name)
    
    if isinstance(table, dict) and "name" in table and table.get("columns"):
        st.success(f"✅ AI successfully generated sophisticated table structure for '{new_table_name}'")
        st.info(f"Generated {len(table.get('columns', []))} columns: {[col.get('name', 'unknown') for col in table.get('columns', [])]}")
        return table
    else:
        st.warning(f"⚠️ AI table generation failed for '{new_table_name}', using enhanced fallback structure")
        if response:
            st.error(f"Failed to parse AI response. Raw content: {response[:500]}...")
    
    # Enhanced fallback structure based on table name analysis and domain context
    table_name_lower = new_table_name.lower()
    
    # First, try to use domain context for intelligent fallback
    if 'project' in domain_context.lower() and 'client' in table_name_lower and 'industry' in table_name_lower:
        # Specific fallback for ClientIndustrySector in project management
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "sector_name", "type": "VARCHAR(255)", "description": "Industry sector name (e.g., Technology, Healthcare, Finance)"},
            {"name": "sector_code", "type": "VARCHAR(50)", "description": "Standard industry classification code"},
            {"name": "description", "type": "TEXT", "description": "Detailed sector description and characteristics"},
            {"name": "is_active", "type": "BOOLEAN", "description": "Whether this sector is currently active"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Record last update timestamp"}
        ]
        # Add foreign keys to existing project-related tables
        foreign_keys = []
        if any('client' in t.lower() for t in table_names):
            client_table = next((t for t in table_names if 'client' in t.lower()), None)
            if client_table:
                foreign_keys.append({"column": "client_id", "references": f"{client_table}(id)"})
        return {
            "name": new_table_name,
            "columns": columns,
            "primary_key": ["id"],
            "foreign_keys": foreign_keys
        }
    
    # Smart fallback based on table name patterns
    elif any(keyword in table_name_lower for keyword in ['user', 'customer', 'client', 'member']):
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "email", "type": "VARCHAR(255)", "description": "Email address"},
            {"name": "first_name", "type": "VARCHAR(100)", "description": "First name"},
            {"name": "last_name", "type": "VARCHAR(100)", "description": "Last name"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Account status"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Registration timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"}
        ]
    elif any(keyword in table_name_lower for keyword in ['order', 'transaction', 'purchase', 'sale']):
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "reference_number", "type": "VARCHAR(100)", "description": "Business reference number"},
            {"name": "total_amount", "type": "DECIMAL(10,2)", "description": "Total monetary amount"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Transaction status"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Transaction timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"}
        ]
    elif any(keyword in table_name_lower for keyword in ['product', 'item', 'inventory', 'catalog']):
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "name", "type": "VARCHAR(255)", "description": "Product name"},
            {"name": "sku", "type": "VARCHAR(100)", "description": "Stock keeping unit"},
            {"name": "price", "type": "DECIMAL(10,2)", "description": "Unit price"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Product status"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Product creation timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"}
        ]
    elif any(keyword in table_name_lower for keyword in ['sector', 'industry', 'category', 'type']):
        # Classification/categorization tables
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "name", "type": "VARCHAR(255)", "description": f"Name of the {table_name_lower.replace('_', ' ')}"},
            {"name": "code", "type": "VARCHAR(50)", "description": "Standardized code or abbreviation"},
            {"name": "description", "type": "TEXT", "description": "Detailed description"},
            {"name": "is_active", "type": "BOOLEAN", "description": "Whether this item is currently active"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Record last update timestamp"}
        ]
    else:
        # Generic business entity fallback
        columns = [
            {"name": "id", "type": "BIGINT", "description": f"Unique identifier for {new_table_name}"},
            {"name": "name", "type": "VARCHAR(255)", "description": f"Name or title for {new_table_name}"},
            {"name": "description", "type": "TEXT", "description": f"Detailed description"},
            {"name": "status", "type": "VARCHAR(50)", "description": "Current status"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
            {"name": "updated_at", "type": "TIMESTAMP", "description": "Record last update timestamp"}
        ]
    
    return {
        "name": new_table_name,
        "columns": columns,
        "primary_key": ["id"],
        "foreign_keys": []
    }














