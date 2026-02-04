"""
Chat Assist Service - Natural Language to SQL Query Generator

This package provides a REST API endpoint that converts natural language queries
into SQL queries, executes them against the IBM Skills Profile DB2 database,
and returns the results.

Components:
- main.py: FastAPI application with /query endpoint
- sql_query_generator.py: Watsonx.ai powered SQL generation
- db_client.py: DB2 database client
- config.py: Configuration management
"""

__version__ = "1.0.0"
__author__ = "IBM Skills Profile Team"

from sql_query_generator import SQLQueryGenerator
from db_client import DB2Client
from config import Config

__all__ = ["SQLQueryGenerator", "DB2Client", "Config"]

# Made with Bob
