# filename: sql_query_service.py

import os
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Watsonx.ai SDK
from ibm_watson_machine_learning.foundation_models import Model
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Database schema and examples
# -----------------------------
TABLE_SCHEMAS = """
TABLE: users
- user_id INTEGER PRIMARY KEY (unique user ID, auto-increment)
- talent_id VARCHAR(20) UNIQUE NOT NULL (external IBM talent ID)
- w3_id VARCHAR(50) UNIQUE NOT NULL (IBM W3 ID)
- user_name VARCHAR(200) NOT NULL (full name of the user)
- email VARCHAR(255) UNIQUE NOT NULL (email address)
- profile_picture_url VARCHAR(500) (URL to profile picture)
- job_role VARCHAR(200) (job role/title)
- pjrs VARCHAR(255) (PJRS code)
- user_role VARCHAR(10) DEFAULT 'DC' (role: DC, Manager, Admin)
- manager_talent_id VARCHAR(20) (manager's talent ID)
- manager_user_id INTEGER (FK to users.user_id - manager reference)
- is_manager BOOLEAN DEFAULT FALSE (whether user is a manager)
- is_active BOOLEAN DEFAULT TRUE (account active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: products
- product_id INTEGER PRIMARY KEY (unique product ID, auto-increment)
- product_name VARCHAR(200) UNIQUE NOT NULL (product name)
- product_icon VARCHAR(100) UNIQUE NOT NULL (product icon identifier)
- category VARCHAR(100) NOT NULL (product category)
- subcategory VARCHAR(100) (product subcategory)
- product_description VARCHAR(1000) (product description)
- vendor VARCHAR(50) DEFAULT 'IBM' (product vendor)
- is_active BOOLEAN DEFAULT TRUE (product active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: user_product_expertise
- expertise_id INTEGER PRIMARY KEY (unique expertise record ID, auto-increment)
- user_id INTEGER NOT NULL (FK to users.user_id)
- product_id SMALLINT NOT NULL (FK to products.product_id)
- assessment_level CHAR(2) (expertise assessment level: L1, L2, L3, L4)
- expertise_implement BOOLEAN DEFAULT FALSE (can implement)
- expertise_advise BOOLEAN DEFAULT FALSE (can advise)
- expertise_design BOOLEAN DEFAULT FALSE (can design)
- expertise_perform BOOLEAN DEFAULT FALSE (can perform)
- project_count SMALLINT (number of projects with this product)
- has_certification BOOLEAN DEFAULT FALSE (has certification for product)
- certification_url VARCHAR(500) (URL to certification)
- is_primary BOOLEAN DEFAULT FALSE NOT NULL (is this primary expertise)
- record_version SMALLINT (version number for tracking changes)
- approved_by INTEGER (FK to users.user_id - approver)
- approved_at TIMESTAMP (approval timestamp)
- is_active BOOLEAN DEFAULT TRUE (record active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: user_product_assets
- asset_id INTEGER PRIMARY KEY (unique asset ID, auto-increment)
- user_id INTEGER NOT NULL (FK to users.user_id - asset owner)
- product_id SMALLINT NOT NULL (FK to products.product_id)
- asset_name VARCHAR(200) NOT NULL (name/title of the asset)
- asset_description VARCHAR(1000) NOT NULL (detailed description)
- repository_url VARCHAR(500) NOT NULL (URL to asset repository)
- platform_type VARCHAR(50) NOT NULL (platform: GitHub, GitLab, etc.)
- url_validated BOOLEAN DEFAULT FALSE (URL validation status)
- users_count SMALLINT (number of users using this asset)
- projects_count SMALLINT (number of projects using this asset)
- time_saved_hours SMALLINT (estimated time saved in hours)
- approval_status VARCHAR(20) (status: PENDING, APPROVED, REJECTED)
- manager_feedback VARCHAR(2000) (manager's feedback)
- approved_by INTEGER (FK to users.user_id - approver)
- approved_at TIMESTAMP (approval timestamp)
- record_version SMALLINT (version number)
- is_active BOOLEAN DEFAULT TRUE (record active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: user_product_knowledge_sharing
- knowledge_id INTEGER PRIMARY KEY (unique knowledge sharing record ID, auto-increment)
- user_id INTEGER NOT NULL (FK to users.user_id)
- product_id SMALLINT NOT NULL (FK to products.product_id)
- content_title VARCHAR(300) NOT NULL (title of shared content)
- content_type VARCHAR(50) NOT NULL (type: Blog, Video, Tutorial, etc.)
- content_url VARCHAR(500) NOT NULL (URL to content)
- platform_type VARCHAR(50) NOT NULL (platform: Medium, YouTube, etc.)
- url_validated BOOLEAN DEFAULT FALSE (URL validation status)
- views_count INTEGER (number of views)
- engagement_count INTEGER (engagement metrics)
- reach_count INTEGER (reach metrics)
- approval_status VARCHAR(20) (status: PENDING, APPROVED, REJECTED)
- manager_feedback VARCHAR(2000) (manager's feedback)
- approved_by INTEGER (FK to users.user_id - approver)
- approved_at TIMESTAMP (approval timestamp)
- record_version SMALLINT (version number)
- is_active BOOLEAN DEFAULT TRUE (record active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: submissions
- submission_id INTEGER PRIMARY KEY (unique submission ID, auto-increment)
- user_id INTEGER NOT NULL (FK to users.user_id - submitter)
- manager_id INTEGER NOT NULL (FK to users.user_id - reviewing manager)
- submission_type VARCHAR(20) NOT NULL (type: EXPERTISE, ASSETS, KNOWLEDGE)
- submission_status VARCHAR(20) DEFAULT 'PENDING' (status: PENDING, APPROVED, REJECTED, PARTIAL)
- total_items SMALLINT (total number of items in submission)
- submitted_at TIMESTAMP (submission timestamp)
- reviewed_at TIMESTAMP (review timestamp)
- manager_feedback VARCHAR(2000) (overall manager feedback)
- rejection_reason VARCHAR(500) (reason for rejection)
- is_active BOOLEAN DEFAULT TRUE (record active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: submission_items
- item_id INTEGER PRIMARY KEY (unique item ID, auto-increment)
- submission_id INTEGER NOT NULL (FK to submissions.submission_id)
- item_type VARCHAR(20) NOT NULL (type: EXPERTISE, ASSET, KNOWLEDGE)
- entity_id INTEGER NOT NULL (ID of the actual entity being submitted)
- product_id SMALLINT NOT NULL (FK to products.product_id)
- change_type VARCHAR(10) NOT NULL (type: CREATE, UPDATE, DELETE)
- prev_value TEXT (previous value as JSON/text - CLOB in DB2)
- new_value TEXT (new value as JSON/text - CLOB in DB2)
- approval_status VARCHAR(20) DEFAULT 'PENDING' (status: PENDING, APPROVED, REJECTED)
- rejection_reason VARCHAR(500) (reason for rejection)
- reviewed_by INTEGER (FK to users.user_id - reviewer)
- reviewed_at TIMESTAMP (review timestamp)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: approvals
- approval_id INTEGER PRIMARY KEY (unique approval ID, auto-increment)
- submission_id INTEGER NOT NULL (FK to submissions.submission_id)
- manager_id INTEGER NOT NULL (FK to users.user_id - approving manager)
- decision VARCHAR(10) NOT NULL (decision: APPROVED, REJECTED)
- rejection_reason VARCHAR(2000) (reason for rejection)
- approval_feedback VARCHAR(2000) (approval feedback/comments)
- created_at TIMESTAMP (approval timestamp)

TABLE: notifications
- notification_id INTEGER PRIMARY KEY (unique notification ID, auto-increment)
- user_id INTEGER NOT NULL (FK to users.user_id - recipient)
- notification_type VARCHAR(50) NOT NULL (type: SUBMISSION, APPROVAL, REJECTION, etc.)
- notification_title VARCHAR(200) NOT NULL (notification title)
- notification_message VARCHAR(1000) NOT NULL (notification message)
- related_submission_id INTEGER (FK to submissions.submission_id - related submission)
- is_read BOOLEAN DEFAULT FALSE (read status)
- read_at TIMESTAMP (timestamp when notification was read)
- created_at TIMESTAMP (notification creation timestamp)

"""


# Sample SQL queries for few-shot learning
SAMPLE_QUERIES = """
Example 1:
Query: "List all team members reporting to manager with user_id=121"
SQL: SELECT u.user_id, u.user_name, u.email, u.job_role
     FROM users u
     WHERE u.manager_user_id = 121
       AND u.is_active = TRUE;

Example 2:
Query: "Show all users with API Connect expertise"
SQL: SELECT u.user_id, u.user_name, p.product_name, upe.assessment_level, upe.is_primary
     FROM user_product_expertise upe
     JOIN users u ON upe.user_id = u.user_id
     JOIN products p ON upe.product_id = p.product_id
     WHERE LOWER(p.product_name) LIKE '%api connect%'
       AND upe.is_active = TRUE;

Example 3:
Query: "Top 5 users with most approved assets"
SQL: SELECT u.user_id, u.user_name, COUNT(upa.asset_id) as asset_count
     FROM user_product_assets upa
     JOIN users u ON upa.user_id = u.user_id
     WHERE upa.approval_status = 'APPROVED'
       AND upa.is_active = TRUE
     GROUP BY u.user_id, u.user_name
     ORDER BY asset_count DESC
     FETCH FIRST 5 ROWS ONLY;

Example 4:
Query: "Show all pending submissions for manager_id = 3243"
SQL: SELECT s.submission_id, u.user_name, s.submission_type, s.total_items, s.submitted_at
     FROM submissions s
     JOIN users u ON s.user_id = u.user_id
     WHERE s.manager_id = 3243
       AND s.submission_status = 'PENDING'
       AND s.is_active = TRUE
     ORDER BY s.submitted_at DESC;

Example 5:
Query: "Users with both primary and secondary expertise in different products"
SQL: SELECT DISTINCT u.user_id, u.user_name,
            p1.product_name as primary_product,
            p2.product_name as secondary_product
     FROM user_product_expertise upe1
     JOIN user_product_expertise upe2 ON upe1.user_id = upe2.user_id
     JOIN users u ON u.user_id = upe1.user_id
     JOIN products p1 ON upe1.product_id = p1.product_id
     JOIN products p2 ON upe2.product_id = p2.product_id
     WHERE upe1.is_primary = TRUE
       AND upe2.is_primary = FALSE
       AND upe1.product_id != upe2.product_id
       AND upe1.is_active = TRUE
       AND upe2.is_active = TRUE;

Example 6:
Query: "Most shared knowledge content by platform type"
SQL: SELECT upks.platform_type, COUNT(upks.knowledge_id) as content_count
     FROM user_product_knowledge_sharing upks
     WHERE upks.is_active = TRUE
       AND upks.approval_status = 'APPROVED'
     GROUP BY upks.platform_type
     ORDER BY content_count DESC;

Example 7:
Query: "Users without any approved expertise"
SQL: SELECT u.user_id, u.user_name, u.email
     FROM users u
     LEFT JOIN user_product_expertise upe ON u.user_id = upe.user_id
       AND upe.is_active = TRUE
       AND upe.approved_by IS NOT NULL
     WHERE upe.expertise_id IS NULL
       AND u.is_active = TRUE
       AND u.user_role = 'DC';

Example 8:
Query: "Recent notifications for user_id = 100 that are unread"
SQL: SELECT n.notification_id, n.notification_type, n.notification_title,
            n.notification_message, n.created_at
     FROM notifications n
     WHERE n.user_id = 100
       AND n.is_read = FALSE
     ORDER BY n.created_at DESC;

"""

# -----------------------------
# SQL Query Generator Class
# -----------------------------
class SQLQueryGenerator:
    def __init__(self):
        # Load credentials safely
        self.watson_url = os.getenv("WATSONX_URL", "").strip()
        self.project_id = os.getenv("WATSONX_PROJECT_ID", "").strip()
        self.model_id = os.getenv("WATSONX_MODEL_ID", "").strip()
        self.api_key = os.getenv("WATSONX_API_KEY", "").strip()

        logger.info(f"Initializing Watsonx model at {self.watson_url}")

        if not all([self.watson_url, self.project_id, self.model_id, self.api_key]):
            raise ValueError("Missing Watsonx.ai credentials in environment variables")

        credentials = {
            "url": self.watson_url,
            "apikey": self.api_key,
        }

        model_params = {
            "decoding_method": "greedy",
            "max_new_tokens": 250,
            "min_new_tokens": 10,
            "repetition_penalty": 1.1,
        }

        try:
            self.model = Model(
                model_id=self.model_id,
                credentials=credentials,
                project_id=self.project_id,
                params=model_params,
            )
            logger.info("Watsonx model initialized successfully")

        except Exception as e:
            logger.error(f"Watsonx initialization failed: {str(e)}")
            raise

    # -----------------------------
    # SQL Cleaner
    # -----------------------------
    def clean_sql_query(self, generated_text: str) -> str:
        """Extract and clean SQL returned by Watsonx."""

        if "```sql" in generated_text:
            generated_text = generated_text.split("```sql")[1].split("```")[0]

        lines = generated_text.strip().split("\n")
        sql_lines = []

        for line in lines:
            line = line.strip()

            if line and not line.lower().startswith(
                ("here", "the", "this", "note:", "explanation:")
            ):
                if line.lower().startswith("sql:"):
                    line = line[4:].strip()

                sql_lines.append(line)

        sql_query = " ".join(sql_lines).replace(";", "").strip()

        if not sql_query.upper().startswith("SELECT"):
            raise ValueError("Generated output is not a valid SELECT statement")

        return sql_query

    # -----------------------------
    # SQL Generation
    # -----------------------------
    def generate_sql_query(self, natural_language_query: str) -> str:
        """
        Generate SQL query from natural language using Watsonx.
        """

        logger.info("Generating SQL query from user request")

        system_prompt = f"""
You are an expert SQL developer. Generate an executable DB2 SQL query.

Return ONLY SQL without explanation.

Natural Language Query:
{natural_language_query}

SQL Query:
"""

        try:
            response = self.model.generate_text(
                prompt=system_prompt,
                guardrails=False,
            )

            sql_query = self.clean_sql_query(response)
            sql_query = sql_query.strip().replace("\n", " ")

            logger.info(f"Generated SQL: {sql_query}")
            return sql_query

        except Exception as e:
            logger.error(f"Watsonx generation error: {str(e)}")
            raise Exception(f"Failed to generate SQL query: {str(e)}")