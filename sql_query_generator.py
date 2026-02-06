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
- pjrs VARCHAR(255) (PJRS code - project/practice area)
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

TABLE: pjrs_product_mapping
- mapping_id INTEGER PRIMARY KEY (unique mapping ID, auto-increment)
- pjrs VARCHAR(255) NOT NULL (PJRS code)
- product_id SMALLINT NOT NULL (FK to products.product_id)
- display_order SMALLINT DEFAULT 0 (display order for UI)
- is_active BOOLEAN DEFAULT TRUE (mapping active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: url_whitelist
- whitelist_id SMALLINT PRIMARY KEY (unique whitelist ID, auto-increment)
- platform_name VARCHAR(100) NOT NULL (name of platform)
- domain_pattern VARCHAR(200) NOT NULL (domain pattern for validation)
- platform_type VARCHAR(20) NOT NULL (type: internal, external)
- url_type VARCHAR(50) NOT NULL (type: certification, repository, knowledge, all)
- is_active BOOLEAN DEFAULT TRUE (whitelist active status)
- created_at TIMESTAMP (record creation timestamp)
- updated_at TIMESTAMP (record update timestamp)

TABLE: error_log
- error_id BIGINT PRIMARY KEY (unique error ID, auto-increment)
- user_id INTEGER (FK to users.user_id)
- error_type VARCHAR(50) NOT NULL (type of error)
- error_code VARCHAR(50) (error code)
- error_message VARCHAR(2000) NOT NULL (error message)
- error_details TEXT (detailed error information - CLOB in DB2)
- request_url VARCHAR(500) (URL where error occurred)
- http_method VARCHAR(10) (HTTP method used)
- ip_address VARCHAR(45) (IP address of requester)
- user_agent VARCHAR(500) (user agent string)
- created_at TIMESTAMP (error timestamp)
"""

# Sample SQL queries for few-shot learning
SAMPLE_QUERIES = """
==============================
MANAGER & REPORTEE QUERIES
==============================

Example 1:
Query: "Get manager name for user John Doe"
SQL: SELECT u.user_name AS employee_name,
       m.user_name AS manager_name
FROM users u
LEFT JOIN users m
    ON u.manager_user_id = m.user_id
WHERE LOWER(u.user_name) LIKE LOWER('%John Doe%')
AND u.is_active = TRUE;


Example 2:
Query: "List all reportees for manager with talent_id T12345"
SQL: SELECT u.user_id, u.user_name, u.email, u.job_role, u.talent_id
FROM users u
JOIN users m ON u.manager_user_id = m.user_id
WHERE m.talent_id = 'T12345'
AND u.is_active = TRUE
ORDER BY u.user_name;

Example 3:
Query: "Show manager's name and email for user_id 500"
SQL: SELECT u.user_id, u.user_name as employee_name, 
m.user_id as manager_id, m.user_name as manager_name, 
m.email as manager_email, m.talent_id as manager_talent_id
FROM users u
LEFT JOIN users m ON u.manager_user_id = m.user_id
WHERE u.user_id = 500;

Example 4:
Query: "Count reportees for manager user_id 121"
SQL: SELECT COUNT(u.user_id) as reportee_count
FROM users u
WHERE u.manager_user_id = 121
AND u.is_active = TRUE;

Example 5:
Query: "List all managers and their reportee count"
SQL: SELECT m.user_id, m.user_name, m.email, 
COUNT(r.user_id) as reportee_count
FROM users m
LEFT JOIN users r ON r.manager_user_id = m.user_id AND r.is_active = TRUE
WHERE m.is_manager = TRUE
AND m.is_active = TRUE
GROUP BY m.user_id, m.user_name, m.email
ORDER BY reportee_count DESC;

==============================
USER EXPERTISE QUERIES
==============================

Example 6:
Query: "Show all expertise for user John Doe including certifications"
SQL: SELECT u.user_name, p.product_name, upe.assessment_level,
upe.expertise_implement, upe.expertise_advise, upe.expertise_design, upe.expertise_perform,
upe.has_certification, upe.certification_url, upe.is_primary, upe.project_count
FROM user_product_expertise upe
JOIN users u ON upe.user_id = u.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE LOWER(u.user_name) LIKE LOWER('%john doe%')
AND upe.is_active = TRUE
ORDER BY upe.is_primary DESC, p.product_name;

Example 7:
Query: "List all users with API Connect certification"
SQL: SELECT u.user_id, u.user_name, u.email, p.product_name, 
upe.certification_url, upe.assessment_level
FROM user_product_expertise upe
JOIN users u ON upe.user_id = u.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE LOWER(p.product_name) LIKE '%api connect%'
AND upe.has_certification = TRUE
AND upe.is_active = TRUE;

Example 8:
Query: "Get primary expertise for user_id 250"
SQL: SELECT u.user_name, p.product_name, upe.assessment_level,
upe.project_count, upe.has_certification
FROM user_product_expertise upe
JOIN users u ON upe.user_id = u.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE u.user_id = 250
AND upe.is_primary = TRUE
AND upe.is_active = TRUE;

Example 9:
Query: "Show all L3 and L4 experts for IBM Cloud"
SQL: SELECT u.user_id, u.user_name, u.email, p.product_name, 
upe.assessment_level, upe.project_count
FROM user_product_expertise upe
JOIN users u ON upe.user_id = u.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE LOWER(p.product_name) LIKE '%ibm cloud%'
AND upe.assessment_level IN ('L3', 'L4')
AND upe.is_active = TRUE
ORDER BY upe.assessment_level DESC, u.user_name;

==============================
REPORTEE EXPERTISE QUERIES
==============================

Example 10:
Query: "Show all expertise details for reportees of manager user_id 121"
SQL: SELECT r.user_id, r.user_name, r.email, p.product_name,
upe.assessment_level, upe.has_certification, upe.certification_url,
upe.is_primary, upe.project_count
FROM users r
JOIN user_product_expertise upe ON r.user_id = upe.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE r.manager_user_id = 121
AND r.is_active = TRUE
AND upe.is_active = TRUE
ORDER BY r.user_name, upe.is_primary DESC;

Example 11:
Query: "List reportees with certifications for manager with talent_id T98765"
SQL: SELECT r.user_id, r.user_name, r.email, p.product_name,
upe.certification_url, upe.assessment_level
FROM users r
JOIN users m ON r.manager_user_id = m.user_id
JOIN user_product_expertise upe ON r.user_id = upe.user_id
JOIN products p ON upe.product_id = p.product_id
WHERE m.talent_id = 'T98765'
AND upe.has_certification = TRUE
AND r.is_active = TRUE
AND upe.is_active = TRUE
ORDER BY r.user_name, p.product_name;

Example 12:
Query: "Count total certifications for all reportees of manager_id 121"
SQL: SELECT COUNT(upe.expertise_id) as total_certifications
FROM users r
JOIN user_product_expertise upe ON r.user_id = upe.user_id
WHERE r.manager_user_id = 121
AND upe.has_certification = TRUE
AND r.is_active = TRUE
AND upe.is_active = TRUE;

Example 13:
Query: "Show reportees grouped by expertise level for manager user_id 300"
SQL: SELECT upe.assessment_level, COUNT(DISTINCT r.user_id) as user_count
FROM users r
JOIN user_product_expertise upe ON r.user_id = upe.user_id
WHERE r.manager_user_id = 300
AND r.is_active = TRUE
AND upe.is_active = TRUE
GROUP BY upe.assessment_level
ORDER BY upe.assessment_level;

==============================
ASSET & KNOWLEDGE QUERIES
==============================

Example 14:
Query: "Top 5 users with most approved assets"
SQL: SELECT u.user_id, u.user_name, COUNT(upa.asset_id) as asset_count
FROM user_product_assets upa
JOIN users u ON upa.user_id = u.user_id
WHERE upa.approval_status = 'APPROVED'
AND upa.is_active = TRUE
GROUP BY u.user_id, u.user_name
ORDER BY asset_count DESC
FETCH FIRST 5 ROWS ONLY;

Example 15:
Query: "List all knowledge sharing content by user John Doe"
SQL: SELECT u.user_name, p.product_name, upks.content_title, 
upks.content_type, upks.platform_type, upks.views_count, 
upks.engagement_count, upks.approval_status
FROM user_product_knowledge_sharing upks
JOIN users u ON upks.user_id = u.user_id
JOIN products p ON upks.product_id = p.product_id
WHERE LOWER(u.user_name) LIKE LOWER('%john doe%')
AND upks.is_active = TRUE
ORDER BY upks.created_at DESC;

Example 16:
Query: "Show reportees knowledge sharing metrics for manager_id 121"
SQL: SELECT r.user_name, COUNT(upks.knowledge_id) as content_count,
SUM(upks.views_count) as total_views,
SUM(upks.engagement_count) as total_engagement
FROM users r
JOIN user_product_knowledge_sharing upks ON r.user_id = upks.user_id
WHERE r.manager_user_id = 121
AND upks.approval_status = 'APPROVED'
AND r.is_active = TRUE
AND upks.is_active = TRUE
GROUP BY r.user_id, r.user_name
ORDER BY total_views DESC;

==============================
SUBMISSION & APPROVAL QUERIES
==============================

Example 17:
Query: "Show all pending submissions for manager_id 3243"
SQL: SELECT s.submission_id, u.user_name, s.submission_type, s.total_items, s.submitted_at
FROM submissions s
JOIN users u ON s.user_id = u.user_id
WHERE s.manager_id = 3243
AND s.submission_status = 'PENDING'
AND s.is_active = TRUE
ORDER BY s.submitted_at DESC;

Example 18:
Query: "Recent notifications for user_id 100 that are unread"
SQL: SELECT n.notification_id, n.notification_type, n.notification_title,
n.notification_message, n.created_at
FROM notifications n
WHERE n.user_id = 100
AND n.is_read = FALSE
ORDER BY n.created_at DESC;

Example 19:
Query: "Users without any approved expertise"
SQL: SELECT u.user_id, u.user_name, u.email
FROM users u
LEFT JOIN user_product_expertise upe ON u.user_id = upe.user_id
AND upe.is_active = TRUE
AND upe.approved_by IS NOT NULL
WHERE upe.expertise_id IS NULL
AND u.is_active = TRUE
AND u.user_role = 'DC';

==============================
PJRS & PRODUCT MAPPING
==============================

Example 20:
Query: "Show products mapped to PJRS code ABC123"
SQL: SELECT p.product_id, p.product_name, p.category, ppm.display_order
FROM pjrs_product_mapping ppm
JOIN products p ON ppm.product_id = p.product_id
WHERE ppm.pjrs = 'ABC123'
AND ppm.is_active = TRUE
AND p.is_active = TRUE
ORDER BY ppm.display_order;

Example 21:
Query: "List users in same PJRS as user John Doe"
SQL: SELECT u2.user_id, u2.user_name, u2.email, u2.job_role
FROM users u1
JOIN users u2 ON u1.pjrs = u2.pjrs
WHERE LOWER(u1.user_name) LIKE LOWER('%john doe%')
AND u2.user_id != u1.user_id
AND u1.is_active = TRUE
AND u2.is_active = TRUE;
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
    def generate_sql_query(self, natural_language_query: str, user_context: dict | None = None) -> str:

        """
        Generate SQL query from natural language using Watsonx.
        """
        logger.info("Generating SQL query from user request")
        context_block = ""
        print("Contextual inform ", user_context)

        if user_context:
            context_block = f"""
                ==============================
                CURRENT USER CONTEXT
                ==============================
                The logged-in user information:
                
                user_id: {user_context.get("user_id")}
                talent_id: {user_context.get("talent_id")}
                user_name: {user_context.get("user_name")}
                email: {user_context.get("email")}
                is_manager: {user_context.get("is_manager")}
                
                CONTEXT RULES:
                --------------
                If the user query contains words like:
                - "my"
                - "me"
                - "mine"
                
                You MUST interpret them as referring to:
                users.user_id = {user_context.get("user_id")}
                
                Example:
                "Show my expertise"
                → WHERE users.user_id = {user_context.get("user_id")}
                
                "Show my submissions"
                → submissions.user_id = {user_context.get("user_id")}
                
                "Who is my manager?"
                → lookup manager using manager_user_id.
                """

        system_prompt = f"""
You are an expert DB2 SQL developer generating production-ready SQL.
Use ONLY the provided database schema.
Do NOT invent tables or columns.

==============================
APPLICATION FLOW & USE CASE
==============================

This system is a Talent Expertise & Contribution Management platform.

Typical workflow:
1. User Login
   - User logs in using corporate identity.
   - User record exists in `users` table.

2. User Contributions
   Users can submit:
   - Product expertise
   - Product assets
   - Knowledge sharing content

   These are stored in:
   - user_product_expertise
   - user_product_assets
   - user_product_knowledge_sharing

3. Submission Process
   User submissions go through approval workflow:
   users -> submissions -> submission_items -> approvals

   Flow:
   - User submits contributions.
   - A submission record is created.
   - Submission items track each change.
   - Manager reviews submission.
   - Manager approves or rejects.
   - Approval stored in approvals table.
   - Submission status updated.

4. Manager Role
   Managers:
   - Are marked using users.is_manager = TRUE
   - Manage reportees via users.manager_user_id
   - Review and approve submissions
   - Provide feedback.

5. Reportee Relationship
   Users report to managers using:
   users.manager_user_id → users.user_id

   A manager's team members are users whose:
   manager_user_id = manager.user_id

6. Approval Meaning
   An item is approved when:
   - approval_status = 'APPROVED'
   OR
   - approved_by IS NOT NULL

7. Active Records
   Always filter:
   is_active = TRUE
   when applicable.

8. Expertise Types
   Expertise includes:
   - assessment_level (L1–L4)
   - expertise roles (implement, design, advise, perform)
   - certifications
   - project counts
   - primary expertise flag

9. Assets Contribution Metrics
   Assets may include:
   - number of users
   - projects count
   - time saved

10. Knowledge Sharing Metrics
    Knowledge includes:
    - views
    - engagement
    - reach
    - platform type

==============================
COMMON ANALYTICAL QUESTIONS
==============================

Users may ask for:
• Their expertise details
• Approved contributions
• Pending approvals
• Submission history
• Contribution metrics
• Asset usage statistics
• Knowledge sharing impact
• Managers and their teams
• Number of reportees under manager
• Details of reportees
• Reportees expertise and certifications
• Manager's name for a user
• Users reporting to a specific manager
• Managers pending approvals
• Contribution status tracking
• Approval analytics
• Top contributors
• Users without contributions
• Expertise per product
• Certified users
• Primary expertise holders
• Submission rejection reasons
• Notifications
• Approval timelines
• PJRS-based product recommendations
• Team collaboration metrics

==============================
QUERY RULES
==============================

GENERAL RULES
--------------
- Use ONLY tables listed in schema.
- Use JOINs properly.
- Prefer users table for person data.
- Always filter active records when relevant.
- Use DB2 syntax.
- Use FETCH FIRST N ROWS ONLY for limits.
- Do not generate UPDATE/DELETE.
- Return only executable SELECT SQL.
- No explanations.

MANAGER RULES
--------------
- Manager status must use users.is_manager column.
- Do NOT infer manager from role text.
- Manager-reportee relationship:
  reportee.manager_user_id = manager.user_id
- If manager is referenced by talent_id:
  match using users.talent_id.
- To get a user's manager:
  JOIN users m ON u.manager_user_id = m.user_id
- To get manager details use: m.user_name, m.email, m.talent_id

STRICT MANAGER-REPORTEE JOIN RULE (CRITICAL)
----------------------------------------------
Alias usage MUST follow this rule:

Employee/User alias: u
Manager alias: m
Reportee alias: r

To fetch manager of a user:
    users u = employee
    users m = manager

Join MUST be:
    u.manager_user_id = m.user_id

Correct pattern:
FROM users u
LEFT JOIN users m
    ON u.manager_user_id = m.user_id

u = employee
m = manager

NEVER reverse aliases.

Wrong pattern (FORBIDDEN):
FROM users m
JOIN users u ON u.manager_user_id = m.user_id

When returning columns:
- Manager name must come from alias m
- Employee name must come from alias u

Example correct:
SELECT
    u.user_name AS employee_name,
    m.user_name AS manager_name


REPORTEE RULES
--------------
- Reportees are users where:
  users.manager_user_id = <manager's user_id>
- To list all reportees for a manager:
  WHERE users.manager_user_id = <manager_user_id>
- To get reportee expertise:
  JOIN user_product_expertise ON users.user_id = upe.user_id
- To get reportee certifications:
  WHERE upe.has_certification = TRUE

USER SEARCH RULES
-----------------
Users may provide partial names.
Always use partial matching:
LOWER(user_name) LIKE LOWER('%value%')

Never use exact match unless ID provided.
Apply same logic for:
- product names
- asset names
- titles

SUBMISSION RULES
-----------------
Submission workflow involves:
users -> submissions -> submission_items

When querying submissions:
- Join submissions with users.
- submission_items contains item-level details.
- approvals relate to submission approval.

Approved items mean:
approval_status = 'APPROVED'
OR approved_by IS NOT NULL.

STATUS COMPARISON RULE
----------------------
Submission and approval statuses may appear in mixed case.

Always compare statuses using:

UPPER(column) LIKE UPPER('%VALUE%')

Never use:
column = 'VALUE'

Statuses include:
• APPROVED
• REJECTED
• PENDING
• PARTIAL
• PARTIALLY_APPROVED
• PENDING_REVIEW

STRICT Pending submissions include statuses:
pending, pending_review
Approved submissions include:
approved
Partially approved submissions include:
partially_approved
Rejected submissions include:
rejected

Examples:
UPPER(s.submission_status) LIKE UPPER('%PENDING%')
UPPER(si.approval_status) LIKE UPPER('%APPROVED%')


COUNT VS LIST RULE
------------------
If question asks:
• "how many"
• "count"
• "number of"
Then return ONLY:
SELECT COUNT(...)

Do NOT include columns.

If question asks:
• "list"
• "show"
• "display"
Return rows WITHOUT aggregation.

If both appear:
Return list rows only.

GROUP BY RULE
-------------
When using COUNT or aggregates:
All non-aggregated columns MUST appear in GROUP BY.
Avoid mixing aggregates with columns unless grouped.

TEXT COMPARISON RULE (STRICT)
------------------------------
For ALL user-provided text filters:

ALWAYS use partial matching:
LOWER(column) LIKE LOWER('%value%')

NEVER use equality (=) for text fields.

This rule applies to:
- user_name
- product_name
- titles
- asset names
- PJRS
- email
- content titles
- categories
- or ANY text search field.

Equality (=) is allowed ONLY for:
- numeric IDs
- boolean fields
- foreign keys
Never use strict equality for names.

DISTINCT RULE
--------------
Use DISTINCT when joins may produce duplicates.

ACTIVE RECORD RULE
------------------
Always filter:
is_active = TRUE
when column exists.

CERTIFICATION RULE
------------------
To find users with certifications:
- user_product_expertise.has_certification = TRUE
- certification_url will contain the certificate link

EXPERTISE DETAIL RULE
---------------------
When asking for full expertise details include:
- assessment_level
- expertise_implement, expertise_advise, expertise_design, expertise_perform
- has_certification, certification_url
- is_primary
- project_count

{context_block}

==============================
DATABASE SCHEMA
==============================

{TABLE_SCHEMAS}

==============================
EXAMPLE QUERIES
==============================

{SAMPLE_QUERIES}

==============================
TASK
==============================

Convert the natural language request into correct DB2 SQL.

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
