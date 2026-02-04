import ibm_db
import os
import json
from dotenv import load_dotenv

import json
from datetime import date, datetime

load_dotenv()


class DB2Client:
    def __init__(self):
        """
        Initializes the DB2 client using environment variables for credentials.
        Environment variables:
            DB2_USERNAME
            DB2_PASSWORD
            DB2_HOSTNAME
            DB2_PORT
            DB2_DATABASE
        """
        self.username = os.getenv("DB2_USERNAME")
        self.password = os.getenv("DB2_PASSWORD")
        self.hostname = os.getenv("DB2_HOSTNAME")
        self.port = os.getenv("DB2_PORT")
        self.database = os.getenv("DB2_DATABASE")
        self.conn = None
        print(self.hostname)
        if not all([self.username, self.password, self.hostname, self.port, self.database]):
            raise ValueError("Please set all required environment variables: DB2_USERNAME, DB2_PASSWORD, DB2_HOSTNAME, DB2_PORT, DB2_DATABASE")

    def connect(self):
        """
        Connects to DB2 using SSL without certificate verification.
        """
        try:
            connection_string = (
                f"DATABASE={self.database};"
                f"HOSTNAME={self.hostname};"
                f"PORT={self.port};"
                f"PROTOCOL=TCPIP;"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"SECURITY=;"  # SSL ON, no cert verification
            )
            self.conn = ibm_db.connect(connection_string, "", "")
            print("✅ Connected successfully.")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to DB2: {e}")

    def execute_query(self, query: str):
        """
        Executes a query and returns the result as a list of dicts.
        """
        if self.conn is None:
            raise ConnectionError("Connection not established. Call connect() first.")
        print(query)
        try:
            stmt = ibm_db.exec_immediate(self.conn, query)
            results = []
            row = ibm_db.fetch_assoc(stmt)
            print("row:",row)
            while row:
                results.append(row)
                row = ibm_db.fetch_assoc(stmt)
            return results
        except Exception as e:
            raise RuntimeError(f"Query execution failed: {e}")
    
    def execute_non_query(self, query: str):
        """
        Executes an INSERT, UPDATE, or DELETE statement.
        Does not return rows.
        """
        if self.conn is None:
            raise ConnectionError("Connection not established. Call connect() first.")

        try:
            stmt = ibm_db.exec_immediate(self.conn, query)
            return True  # success flag
        except Exception as e:
            raise RuntimeError(f"Non-query execution failed: {e}")
    def execute_non_query(self, query: str):
        """
        Executes an INSERT, UPDATE, or DELETE statement.
        Does not return rows.
        """
        if self.conn is None:
            raise ConnectionError("Connection not established. Call connect() first.")

        try:
            stmt = ibm_db.exec_immediate(self.conn, query)
            return True  # success flag
        except Exception as e:
            raise RuntimeError(f"Non-query execution failed: {e}")

    # def save_results_to_json(self, results, filename="query_results.json"):
    #     """
    #     Saves the query results to a JSON file.
    #     """
    #     with open(filename, "w") as f:
    #         json.dump(results, f, indent=4)
    #     print(f"✅ Results saved to {filename}")

 

    def serialize_json(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()  # Convert to string
        return str(obj)  

    def save_results_to_json(self, results, filename="query_results.json"):
        def serialize_json(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return str(obj)  # fallback for other types
        with open(filename, "w") as f:
            json.dump(results, f, indent=4, default=serialize_json)
        print(f"✅ Results saved to {filename}")

    
    
    

    def close(self):
        """
        Closes the DB2 connection.
        """
        if self.conn:
            ibm_db.close(self.conn)
            print("✅ Connection closed.")


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Example: make sure environment variables are set
    os.environ["DB2_USERNAME"] = "db2inst1"
    os.environ["DB2_PASSWORD"] = "db2@1234567890I"
    os.environ["DB2_HOSTNAME"] = "9.30.122.32"
    os.environ["DB2_PORT"] = "25010"
    os.environ["DB2_DATABASE"] = "SKILLSDB"


    # query = "SELECT * FROM MLR04294.PRODUCTS FETCH FIRST 10 ROWS ONLY"
    query = "SELECT * FROM FSQ87086.users"

    db_client = DB2Client()
    db_client.connect()
    results = db_client.execute_query(query)
    # db_client.save_results_to_json(results, "products.json")
    # db_client.save_results_to_json(results, "users.json")
    db_client.close()
