"""
Synthetic Data on Demand (SDoD) module.

Ports the original Streamlit "Synthetic Data on Demand" pipeline
(intent -> clarifying questions -> schema -> editable schema -> generated
tables -> consolidated + augmented dataset) into a clean, dependency-free
REST API.

Design notes (why this is a *clever* reactification, not a 1:1 port):
  - The original app called an LLM (Gemini / local LLM) for every step:
    generating clarifying questions, generating the schema, and generating
    every single column's values. That makes it slow, flaky, and requires
    an API key to even demo.
  - Here we keep the exact same 5-step UX (Intent -> Schema -> Edit ->
    Generate -> Augment) but replace the LLM calls with a fast, deterministic,
    domain-aware template engine. It runs instantly and requires zero
    external services or API keys, matching the "Local (offline)" philosophy
    already used by the GPAI embeddings pipeline in this deployment.
  - The schema shape (tables / columns / primary_key / foreign_keys /
    relationships) is preserved from the original app so the "Upload JSON
    Schema" concept and the editing UX still make sense.
"""
from __future__ import annotations

import io
import json
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests

random.seed(11)
np.random.seed(11)

# ----------------------------------------------------------------------------
# In-memory state (single-user demo, mirrors the other modules in this app)
# ----------------------------------------------------------------------------
STATE: Dict[str, Any] = {
    "intent": None,
    "domain": None,
    "questions": [],
    "questions_source": None,  # "offline" | "llm"
    "answers": {},
    "schema": None,
    "schema_source": None,  # "generated" | "uploaded" | "llm"
    "tables": {},  # table_name -> list[dict] (raw generated rows)
    "consolidated": None,  # pd.DataFrame
    "augmented": None,  # pd.DataFrame (after business rules)
    "rows_per_table": 60,
    "last_rule_message": None,
    "llm_provider": "offline",  # "offline" | "openai" | "gemini"
    "llm_api_key": None,
    "llm_last_error": None,
}


def _reset_downstream(from_step: str) -> None:
    """Clear state for steps strictly after `from_step`, since that step's
    output has just been (re)computed and anything depending on it is stale."""
    order = ["intent", "schema", "generate", "augment"]
    idx = order.index(from_step)
    remaining = order[idx + 1 :]
    if "schema" in remaining:
        STATE["schema"] = None
        STATE["schema_source"] = None
    if "generate" in remaining:
        STATE["tables"] = {}
        STATE["consolidated"] = None
    if "augment" in remaining:
        STATE["augmented"] = None
        STATE["last_rule_message"] = None


# ----------------------------------------------------------------------------
# "Online" LLM connectors (OpenAI / Gemini) — optional, opt-in flavor
# ----------------------------------------------------------------------------
# By default SDoD runs fully offline via the deterministic template engine
# below. If the user connects an OpenAI or Gemini API key, we instead ask the
# real LLM to (a) draft the clarifying questions and (b) draft the schema —
# the two steps where a genuine model gives noticeably richer, more
# domain-specific results. Data generation itself stays on the fast offline
# engine even in "online" mode (calling an LLM per-cell for hundreds of rows
# is what made the original Streamlit app slow and flaky) — but every LLM
# call is wrapped so any failure (bad key, timeout, malformed JSON) silently
# and safely falls back to the offline template engine, so the app can never
# get stuck.
LLM_TIMEOUT_SECONDS = 25


def configure_llm(provider: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    provider = (provider or "offline").strip().lower()
    if provider not in ("offline", "openai", "gemini"):
        raise ValueError("provider must be one of: offline, openai, gemini")
    STATE["llm_provider"] = provider
    STATE["llm_api_key"] = (api_key or "").strip() or None
    STATE["llm_last_error"] = None
    return get_llm_status()


def get_llm_status() -> Dict[str, Any]:
    provider = STATE.get("llm_provider", "offline")
    return {
        "provider": provider,
        "connected": provider != "offline" and bool(STATE.get("llm_api_key")),
        "last_error": STATE.get("llm_last_error"),
    }


def _extract_json_blob(text: str) -> Optional[Any]:
    """Best-effort extraction of a JSON object/array from a raw LLM response
    (handles ```json fences and leading/trailing prose)."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def _call_openai(prompt: str, api_key: str) -> Optional[str]:
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise data architecture assistant. Always respond with valid JSON only, no prose."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 1500,
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        STATE["llm_last_error"] = f"OpenAI request failed: {e}"
        return None


def _call_gemini(prompt: str, api_key: str) -> Optional[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1500},
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        STATE["llm_last_error"] = f"Gemini request failed: {e}"
        return None


def _call_llm(prompt: str) -> Optional[str]:
    provider = STATE.get("llm_provider", "offline")
    api_key = STATE.get("llm_api_key")
    if provider == "offline" or not api_key:
        return None
    if provider == "openai":
        return _call_openai(prompt, api_key)
    if provider == "gemini":
        return _call_gemini(prompt, api_key)
    return None


def _llm_generate_questions(intent: str) -> Optional[Dict[str, Any]]:
    prompt = f"""A user wants to generate a synthetic relational dataset for: "{intent}"

Return ONLY a JSON object with this exact shape:
{{"domain": "one short lowercase word for the domain, e.g. ecommerce/hr/financial/product/generic",
  "questions": [
    {{"question": "...?", "key": "complexity", "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"]}},
    {{"question": "...?", "key": "flavor", "options": ["...", "...", "..."]}},
    {{"question": "...?", "key": "scale", "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"]}}
  ]}}

The "complexity" and "scale" questions MUST keep exactly those option strings (only reorder is not needed).
The "flavor" question's 3 options should be tailored to the specific domain/intent described above.
No prose, no markdown fences — JSON only."""
    raw = _call_llm(prompt)
    parsed = _extract_json_blob(raw) if raw else None
    if not isinstance(parsed, dict) or "questions" not in parsed:
        return None
    questions = parsed.get("questions")
    if not isinstance(questions, list) or len(questions) < 2:
        return None
    for q in questions:
        if not isinstance(q, dict) or "question" not in q or "options" not in q or "key" not in q:
            return None
    return {"domain": str(parsed.get("domain", "generic")).lower().strip() or "generic", "questions": questions}


def _llm_generate_schema(intent: str, answers: Dict[str, str], domain: str) -> Optional[Dict[str, Any]]:
    prompt = f"""Design a relational database schema for synthetic data generation.

User intent: "{intent}"
Domain: {domain}
User preferences: {json.dumps(answers)}

Return ONLY a JSON object with this exact shape (no prose, no markdown fences):
{{"domain": "{domain}",
  "tables": [
    {{"name": "table_name", "columns": [{{"name": "col_name", "type": "INT|VARCHAR(255)|DECIMAL(10,2)|DATE|TIMESTAMP|BOOLEAN|TEXT", "description": "short description"}}], "primary_key": ["id_column"], "foreign_keys": [{{"column": "fk_column", "references": "other_table(other_pk)"}}]}}
  ]}}

Honor the user's complexity preference for table count (Minimal=2, Standard=3, Rich=5 tables) and make column
names/types realistic for the domain. Every table needs an integer primary key column. Foreign keys must
reference tables that are also included in the schema."""
    raw = _call_llm(prompt)
    parsed = _extract_json_blob(raw) if raw else None
    if not isinstance(parsed, dict):
        return None
    try:
        return normalize_schema(parsed)
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Step 1 — Intent -> domain detection -> clarifying questions
# ----------------------------------------------------------------------------
DOMAIN_KEYWORDS = {
    "financial": ["financial", "transaction", "payment", "banking", "bank", "account", "loan", "invoice", "fintech"],
    "hr": ["employee", "hr", "staff", "payroll", "department", "hiring"],
    "product": ["product", "inventory", "catalog", "warehouse", "supplier"],
    "ecommerce": ["customer", "e-commerce", "ecommerce", "sale", "order", "purchase", "commerce", "shop", "cart"],
}


def detect_domain(intent: str) -> str:
    text = (intent or "").lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(k in text for k in keywords):
            return domain
    return "generic"


QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    "ecommerce": [
        {
            "question": "How complex should the customer/order relationships be?",
            "key": "complexity",
            "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"],
        },
        {
            "question": "What's the primary sales channel?",
            "key": "flavor",
            "options": ["Online marketplace", "Direct-to-consumer", "B2B wholesale"],
        },
        {
            "question": "How large should the generated dataset be?",
            "key": "scale",
            "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"],
        },
    ],
    "hr": [
        {
            "question": "How complex should the org structure be?",
            "key": "complexity",
            "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"],
        },
        {
            "question": "What's the primary company profile?",
            "key": "flavor",
            "options": ["Startup / small team", "Mid-size enterprise", "Large multinational"],
        },
        {
            "question": "How large should the generated dataset be?",
            "key": "scale",
            "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"],
        },
    ],
    "product": [
        {
            "question": "How complex should the catalog/supply chain be?",
            "key": "complexity",
            "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"],
        },
        {
            "question": "What's the primary product category focus?",
            "key": "flavor",
            "options": ["Consumer electronics", "Apparel & accessories", "Industrial parts"],
        },
        {
            "question": "How large should the generated dataset be?",
            "key": "scale",
            "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"],
        },
    ],
    "financial": [
        {
            "question": "How complex should the account/transaction model be?",
            "key": "complexity",
            "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"],
        },
        {
            "question": "What's the primary institution type?",
            "key": "flavor",
            "options": ["Retail bank", "Fintech / neobank", "Investment platform"],
        },
        {
            "question": "How large should the generated dataset be?",
            "key": "scale",
            "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"],
        },
    ],
    "generic": [
        {
            "question": "How complex should the data model be?",
            "key": "complexity",
            "options": ["Minimal (2 tables)", "Standard (3 tables)", "Rich (5 tables)"],
        },
        {
            "question": "What's the general theme of this data?",
            "key": "flavor",
            "options": ["Operational records", "Customer-facing data", "Analytical/reporting data"],
        },
        {
            "question": "How large should the generated dataset be?",
            "key": "scale",
            "options": ["Small (~40 rows/table)", "Medium (~120 rows/table)", "Large (~400 rows/table)"],
        },
    ],
}


def generate_questions(intent: str) -> Dict[str, Any]:
    STATE["intent"] = intent
    STATE["answers"] = {}
    STATE["questions_source"] = "offline"

    llm_result = _llm_generate_questions(intent) if STATE.get("llm_provider", "offline") != "offline" else None
    if llm_result:
        domain = llm_result["domain"]
        questions = llm_result["questions"]
        STATE["questions_source"] = "llm"
    else:
        domain = detect_domain(intent)
        questions = QUESTION_BANK.get(domain, QUESTION_BANK["generic"])

    STATE["domain"] = domain
    STATE["questions"] = questions
    _reset_downstream("intent")
    return {"domain": domain, "questions": questions, "source": STATE["questions_source"]}


def submit_answers(answers: Dict[str, str]) -> Dict[str, Any]:
    STATE["answers"] = answers or {}
    return {"ok": True, "answers": STATE["answers"]}


# ----------------------------------------------------------------------------
# Step 2 — Schema generation (domain-aware table blueprints)
# ----------------------------------------------------------------------------
def _col(name: str, type_: str, description: str = "") -> Dict[str, str]:
    return {"name": name, "type": type_, "description": description}


# Each domain defines an ordered list of table blueprints. Complexity controls
# how many of these tables get included (2 / 3 / 5).
TABLE_BLUEPRINTS: Dict[str, List[Dict[str, Any]]] = {
    "ecommerce": [
        {
            "name": "customers",
            "columns": [
                _col("customer_id", "INT", "Unique customer identifier"),
                _col("full_name", "VARCHAR(255)", "Customer full name"),
                _col("email", "VARCHAR(255)", "Customer email address"),
                _col("signup_date", "DATE", "Account creation date"),
                _col("country", "VARCHAR(255)", "Customer country"),
                _col("loyalty_tier", "VARCHAR(255)", "Loyalty program tier"),
            ],
            "primary_key": ["customer_id"],
            "foreign_keys": [],
        },
        {
            "name": "orders",
            "columns": [
                _col("order_id", "INT", "Unique order identifier"),
                _col("customer_id", "INT", "Ordering customer"),
                _col("order_date", "DATE", "Date the order was placed"),
                _col("order_total", "DECIMAL(10,2)", "Total order value"),
                _col("status", "VARCHAR(255)", "Order fulfillment status"),
            ],
            "primary_key": ["order_id"],
            "foreign_keys": [{"column": "customer_id", "references": "customers(customer_id)"}],
        },
        {
            "name": "products",
            "columns": [
                _col("product_id", "INT", "Unique product identifier"),
                _col("product_name", "VARCHAR(255)", "Product name"),
                _col("category", "VARCHAR(255)", "Product category"),
                _col("unit_price", "DECIMAL(10,2)", "Retail unit price"),
                _col("in_stock", "BOOLEAN", "Whether item is in stock"),
            ],
            "primary_key": ["product_id"],
            "foreign_keys": [],
        },
        {
            "name": "order_items",
            "columns": [
                _col("order_item_id", "INT", "Unique line item identifier"),
                _col("order_id", "INT", "Parent order"),
                _col("product_id", "INT", "Purchased product"),
                _col("quantity", "INT", "Quantity purchased"),
                _col("line_total", "DECIMAL(10,2)", "Line item total"),
            ],
            "primary_key": ["order_item_id"],
            "foreign_keys": [
                {"column": "order_id", "references": "orders(order_id)"},
                {"column": "product_id", "references": "products(product_id)"},
            ],
        },
        {
            "name": "reviews",
            "columns": [
                _col("review_id", "INT", "Unique review identifier"),
                _col("product_id", "INT", "Reviewed product"),
                _col("customer_id", "INT", "Reviewing customer"),
                _col("rating", "INT", "Star rating 1-5"),
                _col("comment", "TEXT", "Review comment text"),
                _col("review_date", "DATE", "Date review was submitted"),
            ],
            "primary_key": ["review_id"],
            "foreign_keys": [
                {"column": "product_id", "references": "products(product_id)"},
                {"column": "customer_id", "references": "customers(customer_id)"},
            ],
        },
    ],
    "hr": [
        {
            "name": "departments",
            "columns": [
                _col("department_id", "INT", "Unique department identifier"),
                _col("department_name", "VARCHAR(255)", "Department name"),
                _col("location", "VARCHAR(255)", "Office location"),
            ],
            "primary_key": ["department_id"],
            "foreign_keys": [],
        },
        {
            "name": "employees",
            "columns": [
                _col("employee_id", "INT", "Unique employee identifier"),
                _col("full_name", "VARCHAR(255)", "Employee full name"),
                _col("email", "VARCHAR(255)", "Work email"),
                _col("department_id", "INT", "Assigned department"),
                _col("hire_date", "DATE", "Date of hire"),
                _col("job_title", "VARCHAR(255)", "Job title"),
            ],
            "primary_key": ["employee_id"],
            "foreign_keys": [{"column": "department_id", "references": "departments(department_id)"}],
        },
        {
            "name": "payroll",
            "columns": [
                _col("payroll_id", "INT", "Unique payroll record identifier"),
                _col("employee_id", "INT", "Employee being paid"),
                _col("pay_date", "DATE", "Pay date"),
                _col("gross_salary", "DECIMAL(10,2)", "Gross salary amount"),
                _col("bonus", "DECIMAL(10,2)", "Bonus amount"),
            ],
            "primary_key": ["payroll_id"],
            "foreign_keys": [{"column": "employee_id", "references": "employees(employee_id)"}],
        },
        {
            "name": "performance_reviews",
            "columns": [
                _col("review_id", "INT", "Unique review identifier"),
                _col("employee_id", "INT", "Reviewed employee"),
                _col("review_date", "DATE", "Review date"),
                _col("score", "INT", "Performance score 1-5"),
                _col("notes", "TEXT", "Reviewer notes"),
            ],
            "primary_key": ["review_id"],
            "foreign_keys": [{"column": "employee_id", "references": "employees(employee_id)"}],
        },
        {
            "name": "positions",
            "columns": [
                _col("position_id", "INT", "Unique position identifier"),
                _col("title", "VARCHAR(255)", "Position title"),
                _col("department_id", "INT", "Owning department"),
                _col("salary_band", "VARCHAR(255)", "Salary band code"),
            ],
            "primary_key": ["position_id"],
            "foreign_keys": [{"column": "department_id", "references": "departments(department_id)"}],
        },
    ],
    "product": [
        {
            "name": "categories",
            "columns": [
                _col("category_id", "INT", "Unique category identifier"),
                _col("category_name", "VARCHAR(255)", "Category name"),
            ],
            "primary_key": ["category_id"],
            "foreign_keys": [],
        },
        {
            "name": "products",
            "columns": [
                _col("product_id", "INT", "Unique product identifier"),
                _col("product_name", "VARCHAR(255)", "Product name"),
                _col("category_id", "INT", "Product category"),
                _col("unit_cost", "DECIMAL(10,2)", "Unit cost"),
                _col("unit_price", "DECIMAL(10,2)", "Unit retail price"),
            ],
            "primary_key": ["product_id"],
            "foreign_keys": [{"column": "category_id", "references": "categories(category_id)"}],
        },
        {
            "name": "suppliers",
            "columns": [
                _col("supplier_id", "INT", "Unique supplier identifier"),
                _col("supplier_name", "VARCHAR(255)", "Supplier company name"),
                _col("country", "VARCHAR(255)", "Supplier country"),
            ],
            "primary_key": ["supplier_id"],
            "foreign_keys": [],
        },
        {
            "name": "inventory_stock",
            "columns": [
                _col("stock_id", "INT", "Unique stock record identifier"),
                _col("product_id", "INT", "Product in stock"),
                _col("warehouse", "VARCHAR(255)", "Warehouse location"),
                _col("quantity_on_hand", "INT", "Units currently in stock"),
                _col("last_updated", "TIMESTAMP", "Last inventory update"),
            ],
            "primary_key": ["stock_id"],
            "foreign_keys": [{"column": "product_id", "references": "products(product_id)"}],
        },
        {
            "name": "purchase_orders",
            "columns": [
                _col("po_id", "INT", "Unique purchase order identifier"),
                _col("supplier_id", "INT", "Supplier fulfilling the order"),
                _col("product_id", "INT", "Product being purchased"),
                _col("order_date", "DATE", "Purchase order date"),
                _col("quantity", "INT", "Units ordered"),
            ],
            "primary_key": ["po_id"],
            "foreign_keys": [
                {"column": "supplier_id", "references": "suppliers(supplier_id)"},
                {"column": "product_id", "references": "products(product_id)"},
            ],
        },
    ],
    "financial": [
        {
            "name": "customers",
            "columns": [
                _col("customer_id", "INT", "Unique customer identifier"),
                _col("full_name", "VARCHAR(255)", "Customer full name"),
                _col("email", "VARCHAR(255)", "Customer email"),
                _col("signup_date", "DATE", "Account opening date"),
                _col("risk_tier", "VARCHAR(255)", "Credit risk tier"),
            ],
            "primary_key": ["customer_id"],
            "foreign_keys": [],
        },
        {
            "name": "accounts",
            "columns": [
                _col("account_id", "INT", "Unique account identifier"),
                _col("customer_id", "INT", "Owning customer"),
                _col("account_type", "VARCHAR(255)", "Account type"),
                _col("balance", "DECIMAL(10,2)", "Current balance"),
                _col("opened_date", "DATE", "Date account was opened"),
            ],
            "primary_key": ["account_id"],
            "foreign_keys": [{"column": "customer_id", "references": "customers(customer_id)"}],
        },
        {
            "name": "transactions",
            "columns": [
                _col("transaction_id", "INT", "Unique transaction identifier"),
                _col("account_id", "INT", "Source account"),
                _col("transaction_date", "TIMESTAMP", "Transaction timestamp"),
                _col("amount", "DECIMAL(10,2)", "Transaction amount"),
                _col("transaction_type", "VARCHAR(255)", "Debit or credit"),
            ],
            "primary_key": ["transaction_id"],
            "foreign_keys": [{"column": "account_id", "references": "accounts(account_id)"}],
        },
        {
            "name": "cards",
            "columns": [
                _col("card_id", "INT", "Unique card identifier"),
                _col("account_id", "INT", "Linked account"),
                _col("card_type", "VARCHAR(255)", "Debit or credit card"),
                _col("issued_date", "DATE", "Card issue date"),
                _col("is_active", "BOOLEAN", "Whether card is active"),
            ],
            "primary_key": ["card_id"],
            "foreign_keys": [{"column": "account_id", "references": "accounts(account_id)"}],
        },
        {
            "name": "branches",
            "columns": [
                _col("branch_id", "INT", "Unique branch identifier"),
                _col("branch_name", "VARCHAR(255)", "Branch name"),
                _col("city", "VARCHAR(255)", "Branch city"),
            ],
            "primary_key": ["branch_id"],
            "foreign_keys": [],
        },
    ],
    "generic": [
        {
            "name": "entities",
            "columns": [
                _col("entity_id", "INT", "Unique entity identifier"),
                _col("name", "VARCHAR(255)", "Entity name"),
                _col("created_date", "DATE", "Creation date"),
                _col("status", "VARCHAR(255)", "Current status"),
            ],
            "primary_key": ["entity_id"],
            "foreign_keys": [],
        },
        {
            "name": "categories",
            "columns": [
                _col("category_id", "INT", "Unique category identifier"),
                _col("category_name", "VARCHAR(255)", "Category name"),
            ],
            "primary_key": ["category_id"],
            "foreign_keys": [],
        },
        {
            "name": "records",
            "columns": [
                _col("record_id", "INT", "Unique record identifier"),
                _col("entity_id", "INT", "Related entity"),
                _col("category_id", "INT", "Related category"),
                _col("value", "DECIMAL(10,2)", "Numeric value"),
                _col("recorded_date", "DATE", "Date recorded"),
            ],
            "primary_key": ["record_id"],
            "foreign_keys": [
                {"column": "entity_id", "references": "entities(entity_id)"},
                {"column": "category_id", "references": "categories(category_id)"},
            ],
        },
        {
            "name": "events",
            "columns": [
                _col("event_id", "INT", "Unique event identifier"),
                _col("entity_id", "INT", "Related entity"),
                _col("event_type", "VARCHAR(255)", "Type of event"),
                _col("event_timestamp", "TIMESTAMP", "Event timestamp"),
            ],
            "primary_key": ["event_id"],
            "foreign_keys": [{"column": "entity_id", "references": "entities(entity_id)"}],
        },
        {
            "name": "tags",
            "columns": [
                _col("tag_id", "INT", "Unique tag identifier"),
                _col("entity_id", "INT", "Tagged entity"),
                _col("label", "VARCHAR(255)", "Tag label"),
            ],
            "primary_key": ["tag_id"],
            "foreign_keys": [{"column": "entity_id", "references": "entities(entity_id)"}],
        },
    ],
}

COMPLEXITY_TABLE_COUNT = {
    "Minimal (2 tables)": 2,
    "Standard (3 tables)": 3,
    "Rich (5 tables)": 5,
}

SCALE_ROWS = {
    "Small (~40 rows/table)": 40,
    "Medium (~120 rows/table)": 120,
    "Large (~400 rows/table)": 400,
}


def _relationships_from_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rels = []
    for table in tables:
        for fk in table.get("foreign_keys", []):
            m = re.match(r"^(\w+)\((\w+)\)$", fk["references"])
            if not m:
                continue
            ref_table, ref_col = m.group(1), m.group(2)
            rels.append(
                {
                    "from_table": table["name"],
                    "from_column": fk["column"],
                    "to_table": ref_table,
                    "to_column": ref_col,
                }
            )
    return rels


def build_schema(intent: str, answers: Dict[str, str]) -> Dict[str, Any]:
    domain = STATE.get("domain") or detect_domain(intent)
    scale_label = answers.get("scale", "Medium (~120 rows/table)")
    rows_per_table = SCALE_ROWS.get(scale_label, 120)

    if STATE.get("llm_provider", "offline") != "offline":
        llm_schema = _llm_generate_schema(intent, answers, domain)
        if llm_schema:
            STATE["schema"] = llm_schema
            STATE["schema_source"] = "llm"
            STATE["rows_per_table"] = rows_per_table
            _reset_downstream("schema")
            return llm_schema
        # Fall through to the offline template engine on any LLM failure.

    blueprint = TABLE_BLUEPRINTS.get(domain, TABLE_BLUEPRINTS["generic"])

    complexity_label = answers.get("complexity", "Standard (3 tables)")
    table_count = COMPLEXITY_TABLE_COUNT.get(complexity_label, 3)
    table_count = max(2, min(table_count, len(blueprint)))

    # Keep only tables whose foreign keys reference tables that are also included
    selected = blueprint[:table_count]
    selected_names = {t["name"] for t in selected}
    tables: List[Dict[str, Any]] = []
    for t in selected:
        t_copy = {
            "name": t["name"],
            "columns": [dict(c) for c in t["columns"]],
            "primary_key": list(t["primary_key"]),
            "foreign_keys": [
                dict(fk) for fk in t["foreign_keys"] if re.match(r"^(\w+)\(", fk["references"]).group(1) in selected_names
            ],
        }
        tables.append(t_copy)

    schema = {
        "domain": domain,
        "tables": tables,
        "relationships": _relationships_from_tables(tables),
    }

    STATE["schema"] = schema
    STATE["schema_source"] = "generated"
    STATE["rows_per_table"] = rows_per_table
    _reset_downstream("schema")
    return schema


def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a schema dict has the required keys, filling in sane defaults."""
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a JSON object")
    tables = schema.get("tables", [])
    if not isinstance(tables, list) or len(tables) == 0:
        raise ValueError("Schema must contain a non-empty 'tables' array")
    for table in tables:
        if "name" not in table or not str(table["name"]).strip():
            raise ValueError("Every table must have a non-empty 'name'")
        table.setdefault("columns", [])
        table.setdefault("primary_key", [])
        table.setdefault("foreign_keys", [])
        for col in table["columns"]:
            col.setdefault("type", "VARCHAR(255)")
            col.setdefault("description", "")
    schema.setdefault("relationships", _relationships_from_tables(tables))
    schema.setdefault("domain", schema.get("domain", "generic"))
    return schema


def set_schema(schema: Dict[str, Any], source: str = "uploaded") -> Dict[str, Any]:
    schema = normalize_schema(schema)
    STATE["schema"] = schema
    STATE["schema_source"] = source
    _reset_downstream("schema")
    return schema


def update_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    schema = normalize_schema(schema)
    STATE["schema"] = schema
    _reset_downstream("generate")
    return schema


# ----------------------------------------------------------------------------
# Step 3 (implicit) — value generation helpers
# ----------------------------------------------------------------------------
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Sam",
               "Priya", "Wei", "Fatima", "Diego", "Elena", "Noah", "Mia", "Liam", "Zara", "Omar"]
LAST_NAMES = ["Smith", "Johnson", "Lee", "Garcia", "Chen", "Patel", "Kim", "Novak", "Rossi", "Muller",
              "Silva", "Nguyen", "Andersson", "Kowalski", "Haddad", "Yamada", "Costa", "Fischer", "Dubois", "Khan"]
CATEGORY_WORDS = ["Alpha", "Beta", "Prime", "Core", "Pro", "Max", "Lite", "Plus", "Edge", "Nova"]
STATUS_WORDS = ["Active", "Pending", "Completed", "Cancelled", "On Hold"]
COUNTRIES = ["United States", "Germany", "Japan", "Brazil", "India", "United Kingdom", "France", "Canada", "Australia", "UAE"]
DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Finance", "Operations", "Human Resources", "Support"]
JOB_TITLES = ["Analyst", "Manager", "Engineer", "Coordinator", "Director", "Specialist", "Associate"]

_id_counters: Dict[str, int] = {}


def _next_id(table_name: str) -> int:
    _id_counters[table_name] = _id_counters.get(table_name, 0) + 1
    return _id_counters[table_name]


def _random_date(days_back: int = 900) -> str:
    d = datetime.now() - timedelta(days=random.randint(0, days_back))
    return d.strftime("%Y-%m-%d")


def _random_timestamp(days_back: int = 900) -> str:
    d = datetime.now() - timedelta(days=random.randint(0, days_back), seconds=random.randint(0, 86400))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def _random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _generate_value(col_name: str, col_type: str, table_name: str) -> Any:
    name_l = col_name.lower()
    type_l = col_type.upper()

    if name_l.endswith("_id") and name_l != f"{table_name[:-1] if table_name.endswith('s') else table_name}_id":
        # Foreign-key-like column that isn't this table's own PK — handled separately during FK resolution.
        return None
    if "email" in name_l:
        person = _random_name().lower().replace(" ", ".")
        return f"{person}{random.randint(1, 999)}@example.com"
    if "name" in name_l and "category" not in name_l and "department" not in name_l and "supplier" not in name_l and "branch" not in name_l:
        return _random_name()
    if "category" in name_l or "department" in name_l and "id" not in name_l:
        return f"{random.choice(CATEGORY_WORDS)} {random.choice(['Group', 'Division', 'Line'])}"
    if "country" in name_l:
        return random.choice(COUNTRIES)
    if "status" in name_l:
        return random.choice(STATUS_WORDS)
    if "title" in name_l or "position" in name_l:
        return random.choice(JOB_TITLES)
    if "tier" in name_l or "band" in name_l:
        return random.choice(["Bronze", "Silver", "Gold", "Platinum"])
    if "type" in name_l:
        return random.choice(["Standard", "Premium", "Basic", "Enterprise"])
    if "city" in name_l or "location" in name_l or "warehouse" in name_l:
        return random.choice(["North Hub", "South Hub", "East Depot", "West Depot", "Central"])
    if "comment" in name_l or "note" in name_l or "description" in name_l:
        return f"Auto-generated note #{random.randint(1000, 9999)}"

    if "DECIMAL" in type_l or "PRICE" in name_l or "AMOUNT" in name_l or "SALARY" in name_l or "BALANCE" in name_l or "TOTAL" in name_l or "COST" in name_l or "VALUE" in name_l or "BONUS" in name_l:
        return round(random.uniform(10, 50000), 2)
    if "BOOLEAN" in type_l or name_l.startswith("is_") or name_l.startswith("in_"):
        return random.choice([True, False])
    if "TIMESTAMP" in type_l:
        return _random_timestamp()
    if "DATE" in type_l:
        return _random_date()
    if "INT" in type_l or "BIGINT" in type_l:
        if "quantity" in name_l or "rating" in name_l or "score" in name_l:
            return random.randint(1, 5) if "rating" in name_l or "score" in name_l else random.randint(1, 20)
        return random.randint(1, 1000)

    # Fallback for VARCHAR/TEXT/JSON and anything else
    return f"{col_name.replace('_', ' ').title()} {random.randint(1, 999)}"


def generate_all_data(rows_per_table: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    schema = STATE.get("schema")
    if not schema:
        raise ValueError("No schema available — generate or upload a schema first")

    rows = rows_per_table or STATE.get("rows_per_table", 60)
    tables = schema["tables"]
    generated: Dict[str, List[Dict[str, Any]]] = {}
    pk_pools: Dict[str, List[Any]] = {}

    for table in tables:
        table_name = table["name"]
        pk_cols = table.get("primary_key", [])
        fk_map = {fk["column"]: fk["references"] for fk in table.get("foreign_keys", [])}
        records = []
        for _ in range(rows):
            record: Dict[str, Any] = {}
            for col in table["columns"]:
                col_name = col["name"]
                if col_name in pk_cols:
                    record[col_name] = _next_id(f"{table_name}.{col_name}")
                    continue
                if col_name in fk_map:
                    ref_table = re.match(r"^(\w+)\(", fk_map[col_name]).group(1)
                    pool = pk_pools.get(ref_table)
                    record[col_name] = random.choice(pool) if pool else None
                    continue
                record[col_name] = _generate_value(col_name, col["type"], table_name)
            records.append(record)
        generated[table_name] = records
        for pk in pk_cols:
            pk_pools[table_name] = [r[pk] for r in records]

    STATE["tables"] = generated
    STATE["consolidated"] = consolidate(generated, schema)
    STATE["augmented"] = STATE["consolidated"].copy() if STATE["consolidated"] is not None else None
    return generated


# ----------------------------------------------------------------------------
# Consolidation (port of the original's join logic, simplified)
# ----------------------------------------------------------------------------
def consolidate(generated_data: Dict[str, List[Dict[str, Any]]], schema: Dict[str, Any]) -> pd.DataFrame:
    if not generated_data:
        return pd.DataFrame()

    relationships = schema.get("relationships", [])
    main_table_name, main_rows = max(generated_data.items(), key=lambda kv: len(kv[1] or []))
    if not main_rows:
        return pd.DataFrame()

    consolidated_df = pd.DataFrame(main_rows)

    for table_name, rows in generated_data.items():
        if table_name == main_table_name or not rows:
            continue
        table_df = pd.DataFrame(rows)

        rel = next(
            (
                r
                for r in relationships
                if (r["from_table"] == main_table_name and r["to_table"] == table_name)
                or (r["from_table"] == table_name and r["to_table"] == main_table_name)
            ),
            None,
        )
        if not rel:
            continue

        if rel["from_table"] == main_table_name:
            left_col, right_col = rel["from_column"], rel["to_column"]
        else:
            left_col, right_col = rel["to_column"], rel["from_column"]

        if left_col not in consolidated_df.columns or right_col not in table_df.columns:
            continue

        renamed = table_df.rename(columns={c: f"{table_name}_{c}" for c in table_df.columns if c != right_col})
        consolidated_df = consolidated_df.merge(
            renamed, left_on=left_col, right_on=right_col, how="left", suffixes=("", f"_{table_name}")
        )

    return consolidated_df


# ----------------------------------------------------------------------------
# Step 5 — Augmentation: summary stats + simple business rules
# ----------------------------------------------------------------------------
def augmentation_summary() -> Dict[str, Any]:
    df = STATE.get("augmented")
    if df is None or df.empty:
        return {"rows": 0, "columns": 0, "numeric": [], "categorical": [], "correlations": []}

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "bool"]).columns.tolist()

    numeric_summary = []
    for col in numeric_cols[:8]:
        series = df[col].dropna()
        if series.empty:
            continue
        numeric_summary.append(
            {
                "column": col,
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
                "min": round(float(series.min()), 2),
                "max": round(float(series.max()), 2),
                "std": round(float(series.std() or 0), 2),
            }
        )

    categorical_summary = []
    for col in categorical_cols[:8]:
        counts = df[col].astype(str).value_counts().head(6)
        categorical_summary.append(
            {
                "column": col,
                "unique": int(df[col].nunique()),
                "top_values": [{"label": str(k), "count": int(v)} for k, v in counts.items()],
            }
        )

    correlations = []
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr(numeric_only=True)
        pairs = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1 :]:
                val = corr_matrix.loc[c1, c2]
                if pd.notna(val):
                    pairs.append({"a": c1, "b": c2, "correlation": round(float(val), 3)})
        pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
        correlations = pairs[:6]

    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "numeric": numeric_summary,
        "categorical": categorical_summary,
        "correlations": correlations,
    }


RULE_PATTERN = re.compile(
    r"(increase|decrease|boost|reduce)\s+([a-zA-Z0-9_.` ]+?)\s+by\s+(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def _normalize_col_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def _find_target_columns(df: pd.DataFrame, raw_col: str) -> List[str]:
    """Resolve a user-typed column phrase to actual numeric dataframe columns.

    Tiered matching so ambiguous phrases ("price") don't silently grab the
    wrong column, and so "orders.order_total" / "orders_order_total" style
    table-qualified references (as produced by our own consolidation join)
    resolve precisely:
      1. Exact match (case-insensitive, ignoring punctuation)
      2. Column ends with "_<token>" (e.g. "order_total" -> "orders_order_total")
      3. Column contains "_<token>_" or starts with "<token>_" (word-boundary-ish)
      4. Loose substring match (last resort)
    Only the *first tier that yields any numeric match* is used — we never
    silently fall through to a looser tier if a precise one already matched,
    and within that tier we apply to *all* matching numeric columns rather
    than arbitrarily picking the first, so e.g. "increase price by 10%" with
    both "unit_price" and "list_price" present updates both consistently.
    """
    token = _normalize_col_token(raw_col)
    if not token:
        return []

    normalized = {c: _normalize_col_token(c) for c in df.columns}

    tiers: List[List[str]] = [
        [c for c, n in normalized.items() if n == token],
        [c for c, n in normalized.items() if n.endswith(f"_{token}") or n == token],
        [c for c, n in normalized.items() if f"_{token}_" in f"_{n}_"],
        [c for c, n in normalized.items() if token in n],
    ]

    for tier in tiers:
        numeric_tier = [c for c in tier if pd.api.types.is_numeric_dtype(df[c])]
        if numeric_tier:
            return numeric_tier
    return []


def apply_business_rule(rule_text: str) -> Dict[str, Any]:
    df = STATE.get("augmented")
    if df is None or df.empty:
        return {"ok": False, "message": "No data available — generate data first."}

    match = RULE_PATTERN.search(rule_text or "")
    if not match:
        return {
            "ok": False,
            "message": "Couldn't parse rule. Try a phrase like: 'increase unit_price by 10%'.",
        }

    direction, raw_col, pct_str = match.groups()
    raw_col = raw_col.strip().strip("`")
    pct = float(pct_str) / 100.0
    factor = 1 + pct if direction.lower() in ("increase", "boost") else 1 - pct

    target_columns = _find_target_columns(df, raw_col)
    if not target_columns:
        return {"ok": False, "message": f"No numeric column matching '{raw_col}' was found."}

    for col in target_columns:
        df[col] = (df[col] * factor).round(2)
    STATE["augmented"] = df

    if len(target_columns) == 1:
        message = f"Applied: {direction} '{target_columns[0]}' by {pct_str}% across {len(df)} rows."
    else:
        cols_list = ", ".join(f"'{c}'" for c in target_columns)
        message = f"Applied: {direction} {cols_list} by {pct_str}% across {len(df)} rows."
    STATE["last_rule_message"] = message
    return {"ok": True, "message": message, "columns": target_columns}


def reset_augmentation() -> None:
    if STATE.get("consolidated") is not None:
        STATE["augmented"] = STATE["consolidated"].copy()
        STATE["last_rule_message"] = None


# ----------------------------------------------------------------------------
# Status / preview / export helpers
# ----------------------------------------------------------------------------
def get_status() -> Dict[str, Any]:
    tables = STATE.get("tables") or {}
    consolidated = STATE.get("consolidated")
    augmented = STATE.get("augmented")
    return {
        "intent": STATE.get("intent"),
        "domain": STATE.get("domain"),
        "has_questions": bool(STATE.get("questions")),
        "has_answers": bool(STATE.get("answers")),
        "has_schema": STATE.get("schema") is not None,
        "schema_source": STATE.get("schema_source"),
        "questions_source": STATE.get("questions_source"),
        "table_count": len(STATE["schema"]["tables"]) if STATE.get("schema") else 0,
        "has_data": bool(tables) and any(len(v) for v in tables.values()),
        "table_names": list(tables.keys()),
        "rows_per_table": STATE.get("rows_per_table", 60),
        "consolidated_rows": int(len(consolidated)) if consolidated is not None else 0,
        "consolidated_cols": int(len(consolidated.columns)) if consolidated is not None else 0,
        "has_augmented": augmented is not None and not augmented.empty,
        "last_rule_message": STATE.get("last_rule_message"),
        "llm": get_llm_status(),
    }


def preview_table(table_name: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    tables = STATE.get("tables") or {}
    if not tables:
        return {"columns": [], "rows": [], "available_tables": []}
    name = table_name or next(iter(tables.keys()))
    records = tables.get(name, [])
    columns = list(records[0].keys()) if records else []
    return {
        "table": name,
        "available_tables": list(tables.keys()),
        "columns": columns,
        "rows": records[:limit],
        "total_rows": len(records),
    }


def preview_consolidated(limit: int = 25, augmented: bool = True) -> Dict[str, Any]:
    df = STATE.get("augmented") if augmented else STATE.get("consolidated")
    if df is None or df.empty:
        return {"columns": [], "rows": [], "total_rows": 0}
    safe = df.head(limit).replace({np.nan: None})
    return {
        "columns": list(df.columns),
        "rows": safe.to_dict(orient="records"),
        "total_rows": int(len(df)),
    }


def export_csv(table_name: Optional[str] = None, consolidated: bool = False, augmented: bool = True) -> bytes:
    if consolidated:
        df = STATE.get("augmented") if augmented else STATE.get("consolidated")
        if df is None:
            df = pd.DataFrame()
    else:
        tables = STATE.get("tables") or {}
        name = table_name or next(iter(tables.keys()), None)
        df = pd.DataFrame(tables.get(name, [])) if name else pd.DataFrame()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def reset_all() -> None:
    STATE.update(
        {
            "intent": None,
            "domain": None,
            "questions": [],
            "questions_source": None,
            "answers": {},
            "schema": None,
            "schema_source": None,
            "tables": {},
            "consolidated": None,
            "augmented": None,
            "rows_per_table": 60,
            "last_rule_message": None,
        }
    )
    _id_counters.clear()
