# app.py
import os
import sys
import logging

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from flask import Flask, jsonify, text_type
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import text
except Exception as e:
    # If basic imports fail, Vercel logs will show this
    print(f"CRITICAL IMPORT ERROR: {e}")
    raise

# Minimal App for Vercel
app = Flask(__name__)

@app.route('/')
def index():
    return "StockFlow Live is running. Use /health for diagnosis."

@app.route('/health')
def health():
    info = {
        "status": "online",
        "python": sys.version,
        "env": {k: "SET" for k in os.environ if "DATABASE" in k or "SECRET" in k}
    }
    
    try:
        db_url = os.environ.get('DATABASE_URL', '').strip()
        auth_token = os.environ.get('DATABASE_AUTH_TOKEN', '').strip()
        
        if not db_url:
            info["db"] = "Missing DATABASE_URL"
            return jsonify(info)
            
        # Try direct connection with sqlalchemy
        from sqlalchemy import create_engine
        
        # Dialect registration
        try:
            from sqlalchemy.dialects import registry
            import libsql_client.sqlalchemy
            registry.register("sqlite.libsql", "libsql_client.sqlalchemy", "LibSQLDialect")
        except Exception as reg_err:
            info["reg_error"] = str(reg_err)
            
        final_url = db_url.replace('libsql://', 'sqlite.libsql://')
        if auth_token and 'auth_token=' not in final_url:
            sep = '&' if '?' in final_url else '?'
            final_url += f"{sep}auth_token={auth_token}"
            
        engine = create_engine(final_url)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1")).fetchone()
            info["db"] = "Connected: " + str(res[0])
            
    except Exception as e:
        info["db_error"] = str(e)
        
    return jsonify(info)

# Main entry point for Vercel
if __name__ == "__main__":
    app.run()
