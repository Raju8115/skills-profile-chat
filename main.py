from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any
import uvicorn

from sql_query_generator import SQLQueryGenerator
from db_client import DB2Client
from config import Config

# ---------------- Pydantic models ----------------

class QueryRequest(BaseModel):
    """Request model for natural language query"""
    user_query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "Show all users with API Connect expertise"
            }
        }

class QueryResponse(BaseModel):
    """Response model with query results"""
    success: bool
    natural_query: str
    generated_sql: str
    results: List[Dict[str, Any]]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "natural_query": "Show all users with API Connect expertise",
                "generated_sql": "SELECT u.user_id, u.user_name FROM users u...",
                "results": [{"user_id": 1, "user_name": "John Doe"}],
                "timestamp": "2026-02-03T16:00:00"
            }
        }

# ---------------- FastAPI app ----------------

app = FastAPI(
    title="Chat Assist - Natural Language to SQL",
    description="Convert natural language queries to SQL and execute against Skills Profile database",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
sql_generator: SQLQueryGenerator = None  # type: ignore
db_client: DB2Client = None  # type: ignore

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global sql_generator, db_client
    
    print("\n" + "="*60)
    print("Starting Chat Assist Service")
    print("="*60)
    
    # Print configuration
    Config.print_config()
    
    # Initialize SQL generator
    print("\n🔧 Initializing SQL Query Generator...")
    sql_generator = SQLQueryGenerator()
    print("✅ SQL Query Generator initialized")
    
    # Initialize and connect DB client
    print("\n🔧 Connecting to DB2 database...")
    db_client = DB2Client()
    db_client.connect()
    print("✅ Database connection established")
    
    print("\n" + "="*60)
    print("Chat Assist Service is ready!")
    print("="*60 + "\n")

@app.post("/query", response_model=QueryResponse)
def process_query(request: QueryRequest):
    try:
        user_query = request.user_query.strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Missing user query")

        # Generate SQL from natural language
        sql_query = sql_generator.generate_sql_query(user_query)

        print("SQL part done")
        # Execute the SQL query using DB2Client
        results = db_client.execute_query(sql_query)

        return QueryResponse(
            success=True,
            natural_query=user_query,
            generated_sql=sql_query,
            results=results,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ---------------- Shutdown hook ----------------
@app.on_event("shutdown")
def shutdown_event():
    """Close DB connection when FastAPI shuts down."""
    db_client.close()


# Run app directly with uvicorn
if __name__ == "__main__":
    ...
