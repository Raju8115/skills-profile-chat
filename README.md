# Chat Assist Service - Natural Language to SQL Query Generator

This service provides a REST API endpoint that converts natural language queries into SQL queries, executes them against the IBM Skills Profile DB2 database, and returns the results.

## Overview

The Chat Assist service uses IBM Watsonx.ai foundation models to generate SQL queries from natural language input. It's designed to be used as a tool for AI orchestration systems to query the Skills Profile database.

## Architecture

```
┌─────────────────┐
│  User/AI Agent  │
└────────┬────────┘
         │ Natural Language Query
         ▼
┌─────────────────┐
│   FastAPI App   │
│   (main.py)     │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌──────────────────┐  ┌──────────────────┐
│ SQL Generator    │  │   DB2 Client     │
│ (Watsonx.ai)     │  │   (ibm_db)       │
└──────────────────┘  └──────────────────┘
         │                  │
         └────────┬─────────┘
                  ▼
         ┌─────────────────┐
         │  DB2 Database   │
         │ (Skills Profile)│
         └─────────────────┘
```

## Components

### 1. `main.py`
FastAPI application that exposes the `/query` endpoint.

**Endpoint:** `POST /query`
- **Request Body:**
  ```json
  {
    "user_query": "Show all users with API Connect expertise"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "natural_query": "Show all users with API Connect expertise",
    "generated_sql": "SELECT u.user_id, u.user_name...",
    "results": [...],
    "timestamp": "2026-02-03T16:00:00"
  }
  ```

### 2. `sql_query_generator.py`
Generates SQL queries from natural language using IBM Watsonx.ai.

**Features:**
- Complete database schema awareness
- Few-shot learning with example queries
- DB2-specific SQL syntax
- Query validation and cleaning

**Database Schema Includes:**
- `users` - User profiles and manager relationships
- `products` - Product catalog
- `user_product_expertise` - User expertise levels
- `user_product_assets` - User-created assets/accelerators
- `user_product_knowledge_sharing` - Knowledge sharing content
- `submissions` - Approval workflow submissions
- `submission_items` - Individual submission items
- `approvals` - Manager approval decisions
- `notifications` - User notifications

### 3. `db_client.py`
DB2 database client for executing queries.

**Features:**
- SSL connection support
- Query execution with result serialization
- JSON export capability
- Connection pooling

### 4. `config.py`
Configuration management using environment variables.

**Configuration Variables:**
- Database: `DB2_USERNAME`, `DB2_PASSWORD`, `DB2_HOSTNAME`, `DB2_PORT`, `DB2_DATABASE`, `DB2_SCHEMA`
- Watsonx.ai: `WATSONX_URL`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_MODEL_ID`
- API: `API_HOST`, `API_PORT`, `API_RELOAD`

### 5. `query_generator.json`
OpenAPI specification for the query endpoint (for AI orchestration tools).

## Setup

### Prerequisites
- Python 3.8+
- IBM Cloud DB2 instance
- IBM Watsonx.ai project with API access

### Installation

1. **Install dependencies:**
   ```bash
   cd chatAssist
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   
   The service reads configuration from the `.env` file in the project root. Ensure the following variables are set:

   ```env
   # Database Configuration
   DB2_DATABASE=bludb
   DB2_HOSTNAME=your-db2-hostname.databases.appdomain.cloud
   DB2_PORT=30756
   DB2_USERNAME=your_username
   DB2_PASSWORD=your_password
   DB2_SCHEMA=YOUR_SCHEMA  # Optional

   # Watsonx.ai Configuration
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   WATSONX_API_KEY=your_watsonx_api_key
   WATSONX_PROJECT_ID=your_project_id
   WATSONX_MODEL_ID=ibm/granite-13b-chat-v2
   ```

3. **Run the service:**
   
   From the project root directory:
   ```bash
   uvicorn chatAssist.main:app --reload --port 8085
   ```
   
   Or from within the chatAssist directory:
   ```bash
   cd chatAssist
   python main.py
   ```

   The service will start on `http://127.0.0.1:8085`

## Usage

### Direct API Call

```bash
curl -X POST "http://localhost:8085/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Show all pending submissions for manager_id = 100"
  }'
```

### Python Client

```python
import requests

response = requests.post(
    "http://localhost:8085/query",
    json={"user_query": "List all users with primary expertise in API Connect"}
)

data = response.json()
print(f"Generated SQL: {data['generated_sql']}")
print(f"Results: {data['results']}")
```

### As AI Orchestration Tool

The service can be integrated with AI orchestration platforms (like LangChain, AutoGen, etc.) using the OpenAPI specification in `query_generator.json`.

## Example Queries

1. **User Management:**
   - "List all team members reporting to manager with user_id=121"
   - "Show all active users with email containing '@ibm.com'"

2. **Expertise Queries:**
   - "Show all users with API Connect expertise"
   - "Users with both primary and secondary expertise"
   - "Top 5 users with most approved expertise records"

3. **Asset Queries:**
   - "Top 5 users with most approved assets"
   - "Show all assets with more than 10 users"
   - "Assets created in the last 30 days"

4. **Submission Queries:**
   - "Show all pending submissions for manager_id = 3243"
   - "Recent approved submissions"
   - "Submissions with rejection reasons"

5. **Knowledge Sharing:**
   - "Most shared knowledge content by platform type"
   - "Users with most blog posts"
   - "Knowledge sharing content with high engagement"

## Database Schema

The service has complete awareness of the Skills Profile database schema:

- **users**: User profiles, roles, and manager relationships
- **products**: Product catalog with categories
- **user_product_expertise**: User expertise levels and certifications
- **user_product_assets**: User-created assets and accelerators
- **user_product_knowledge_sharing**: Blogs, videos, tutorials
- **submissions**: Approval workflow submissions
- **submission_items**: Individual items in submissions
- **approvals**: Manager approval decisions
- **notifications**: User notification system

## Security Considerations

1. **Database Access**: Uses SSL connections to DB2
2. **Credentials**: All credentials stored in environment variables
3. **Query Validation**: SQL queries are validated before execution
4. **Read-Only**: Service only executes SELECT queries (no modifications)

## Deployment

### Docker Deployment

A `Dockerfile` is provided for containerized deployment:

```bash
docker build -t chat-assist .
docker run -p 8085:8085 --env-file ../.env chat-assist
```

### IBM Code Engine

The service can be deployed to IBM Code Engine:

1. Build and push container image
2. Create Code Engine application
3. Set environment variables
4. Deploy

## Troubleshooting

### Connection Issues
- Verify DB2 credentials in `.env`
- Check network connectivity to DB2 instance
- Ensure SSL is properly configured

### Query Generation Issues
- **Verify Watsonx.ai credentials**: Ensure all credentials are correct in `.env`
- **Check Watsonx URL format**:
  - For IBM Cloud: `https://us-south.ml.cloud.ibm.com` or `https://eu-gb.ml.cloud.ibm.com`
  - For Cloud Pak for Data: URL should include `cpd` or proper CPD endpoint
- **API key permissions**: Ensure API key has access to Watsonx.ai and the specified project
- **Model availability**: Verify the model ID is available in your region/project
- **Project ID**: Confirm the project ID is correct and accessible with your API key

### Common Watsonx Errors

**Error: "The specified url is not valid"**
- Solution: Check that WATSONX_URL matches your IBM Cloud region
- For Sydney region: `https://au-syd.ml.cloud.ibm.com`
- For US South: `https://us-south.ml.cloud.ibm.com`
- For EU: `https://eu-gb.ml.cloud.ibm.com` or `https://eu-de.ml.cloud.ibm.com`

**Error: "Failed to initialize Watsonx model"**
- Verify all environment variables are set correctly
- Check API key is valid and not expired
- Ensure project ID exists and you have access
- Confirm model ID is available in your project

### Query Execution Errors
- Check SQL syntax compatibility with DB2
- Verify table and column names match schema
- Review query logs for details

## API Documentation

When the service is running, visit:
- Swagger UI: `http://localhost:8085/docs`
- ReDoc: `http://localhost:8085/redoc`

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify environment configuration
3. Review the database schema documentation
4. Contact the development team

## Version History

- **v1.0.0** (2026-02-03): Initial release with complete schema support
  - Natural language to SQL conversion
  - DB2 database integration
  - Watsonx.ai powered query generation
  - Complete Skills Profile schema support