from flask import Blueprint, render_template, request, jsonify, current_app, session, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
import os
import threading
import time
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import text, inspect
from models import db, DbMaintenanceLog, SearchLog
from utils import check_permission

admin_db_maintenance_bp = Blueprint('admin_db_maintenance', __name__)

# Global dictionary to store job status
maintenance_jobs = {}
job_lock = threading.Lock()

def get_db_size():
    """Get the current database file size in MB."""
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if os.path.exists(db_path):
            return os.path.getsize(db_path) / (1024 * 1024)
    return 0

def analyze_indexes(engine):
    """Analyze indexes to find redundant or low-cardinality ones."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    redundant_indexes = []
    
    total_indexes = 0
    
    for table in tables:
        indexes = inspector.get_indexes(table)
        fks = inspector.get_foreign_keys(table)
        fk_column_sets = [set(fk['constrained_columns']) for fk in fks]
        
        # Check for duplicates and left-prefix
        for i, idx1 in enumerate(indexes):
            total_indexes += 1
            is_redundant = False
            reason = ""
            
            if idx1['unique']:
                continue
                
            cols1 = idx1['column_names']
            
            # Skip if index is likely used for a Foreign Key
            # FKs usually require an index on the referencing columns.
            # We skip if the index columns exactly match any FK constraint columns.
            is_fk_related = False
            cols1_set = set(cols1)
            for fk_cols in fk_column_sets:
                if cols1_set == fk_cols:
                    is_fk_related = True
                    break
            if is_fk_related:
                continue
            
            for j, idx2 in enumerate(indexes):
                if i == j:
                    continue
                
                cols2 = idx2['column_names']
                
                if cols1 == cols2:
                    if not idx1['unique'] and idx2['unique']:
                        is_redundant = True
                        reason = f"Duplicate of unique index {idx2['name']}"
                        break
                    elif not idx1['unique'] and not idx2['unique'] and i > j:
                        is_redundant = True
                        reason = f"Duplicate of index {idx2['name']}"
                        break
                
                if len(cols1) < len(cols2) and cols1 == cols2[:len(cols1)]:
                     is_redundant = True
                     reason = f"Left-prefix of index {idx2['name']} {cols2}"
                     break
            
            if is_redundant:
                redundant_indexes.append({
                    'table': table,
                    'index': idx1['name'],
                    'columns': cols1,
                    'reason': reason,
                    'type': 'Redundant'
                })
                continue

            try:
                with engine.connect() as conn:
                    total_rows = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    if total_rows > 1000:
                        # Handle both single and multi-column indexes for cardinality
                        cols_str = ", ".join(cols1)
                        # Use subquery for distinct count on multiple columns which works in SQLite
                        distinct_query = f"SELECT COUNT(*) FROM (SELECT DISTINCT {cols_str} FROM {table})"
                        distinct_count = conn.execute(text(distinct_query)).scalar()
                        
                        if distinct_count is not None and (distinct_count / total_rows) < 0.01:
                            redundant_indexes.append({
                                'table': table,
                                'index': idx1['name'],
                                'columns': cols1,
                                'reason': f"Low cardinality ({distinct_count}/{total_rows})",
                                'type': 'Low Cardinality'
                            })
            except Exception:
                pass

    return redundant_indexes, total_indexes

def perform_repair_job(job_id, app, safe_mode, optimize_table, admin_username):
    """Background job to repair the database."""
    with app.app_context():
        # Log start
        try:
            log_entry = DbMaintenanceLog(
                performed_by=admin_username,
                action_type='repair',
                status='running',
                details=json.dumps({'safe_mode': safe_mode, 'optimize_table': optimize_table})
            )
            db.session.add(log_entry)
            db.session.commit()
            log_id = log_entry.id
        except Exception as e:
            print(f"Failed to create log: {e}")
            log_id = None

        try:
            with job_lock:
                maintenance_jobs[job_id]['status'] = 'running'
                maintenance_jobs[job_id]['progress'] = 0
            
            engine = db.engine
            
            # 1. Analyze
            with job_lock:
                maintenance_jobs[job_id]['message'] = "Analyzing indexes..."
                maintenance_jobs[job_id]['progress'] = 10
            
            redundant_indexes, _ = analyze_indexes(engine)
            
            deleted_indexes = []
            recovery_script = []
            
            total_ops = len(redundant_indexes) + (1 if optimize_table else 0) + 1
            current_op = 0
            
            # 2. Drop Indexes
            for idx_info in redundant_indexes:
                if maintenance_jobs[job_id].get('cancelled'):
                    break
                
                table = idx_info['table']
                index = idx_info['index']
                columns = idx_info['columns']
                
                col_str = ", ".join(columns)
                recovery_sql = f"CREATE INDEX {index} ON {table} ({col_str});"
                recovery_script.append(recovery_sql)
                
                try:
                    with job_lock:
                        maintenance_jobs[job_id]['message'] = f"Dropping index {index} on {table}..."
                    
                    drop_sql = f"DROP INDEX IF EXISTS {index}"
                    with engine.connect() as conn:
                         conn.execute(text(drop_sql))
                         conn.commit()
                    
                    deleted_indexes.append(idx_info)
                    
                except Exception as e:
                    with job_lock:
                        maintenance_jobs[job_id]['error'] = str(e)
                    print(f"Error dropping index {index}: {e}")
                
                current_op += 1
                progress = 10 + int((current_op / total_ops) * 80)
                with job_lock:
                    maintenance_jobs[job_id]['progress'] = progress
            
            # 3. Optimize
            if optimize_table and not maintenance_jobs[job_id].get('cancelled'):
                with job_lock:
                    maintenance_jobs[job_id]['message'] = "Optimizing database (VACUUM)... This may take a while."
                
                try:
                    with engine.connect() as conn:
                        connection = conn.execution_options(isolation_level="AUTOCOMMIT")
                        connection.execute(text("VACUUM"))
                except Exception as e:
                     print(f"Error executing VACUUM: {e}")
                
                current_op += 1
                progress = 10 + int((current_op / total_ops) * 80)
                with job_lock:
                    maintenance_jobs[job_id]['progress'] = progress

            # 4. Final Analyze
            if not maintenance_jobs[job_id].get('cancelled'):
                with job_lock:
                    maintenance_jobs[job_id]['message'] = "Running ANALYZE..."
                
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ANALYZE"))
                        conn.commit()
                except Exception as e:
                     print(f"Error executing ANALYZE: {e}")

            # Finish
            with job_lock:
                status = 'cancelled' if maintenance_jobs[job_id].get('cancelled') else 'completed'
                maintenance_jobs[job_id]['status'] = status
                maintenance_jobs[job_id]['progress'] = 100
                maintenance_jobs[job_id]['result'] = {
                    'deleted_indexes': deleted_indexes,
                    'recovery_script': "\n".join(recovery_script)
                }
            
            # Update Log
            if log_id:
                log_entry = DbMaintenanceLog.query.get(log_id)
                log_entry.status = status
                details = json.loads(log_entry.details or '{}')
                details.update({
                    'deleted_count': len(deleted_indexes),
                    'recovery_script': "\n".join(recovery_script)
                })
                log_entry.details = json.dumps(details)
                db.session.commit()
                
        except Exception as e:
            with job_lock:
                maintenance_jobs[job_id]['status'] = 'failed'
                maintenance_jobs[job_id]['error'] = str(e)
            
            if log_id:
                log_entry = DbMaintenanceLog.query.get(log_id)
                log_entry.status = 'failed'
                log_entry.error_message = str(e)
                db.session.commit()

@admin_db_maintenance_bp.route('/admin/db-maintenance', methods=['GET'])
@login_required
def index():
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return render_template('access_denied.html'), 403
    
    return render_template('admin_db_maintenance.html')

@admin_db_maintenance_bp.route('/admin/db-maintenance/analyze', methods=['POST'])
@login_required
def analyze():
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        db_size = get_db_size()
        engine = db.engine
        redundant_indexes, total_indexes = analyze_indexes(engine)
        
        # Log analysis
        try:
            log_entry = DbMaintenanceLog(
                performed_by=current_user.username,
                action_type='analyze',
                status='success',
                details=json.dumps({
                    'db_size_mb': db_size,
                    'total_indexes': total_indexes,
                    'redundant_count': len(redundant_indexes)
                })
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'db_size_mb': round(db_size, 2),
            'total_indexes': total_indexes,
            'redundant_indexes': redundant_indexes,
            'savings_estimate': "N/A (SQLite)"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@admin_db_maintenance_bp.route('/admin/db-maintenance/cleanup-search-logs', methods=['POST'])
@login_required
def cleanup_search_logs():
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Calculate date 2 months ago
        cutoff_date = date.today() - relativedelta(months=2)
        
        # We delete in chunks to avoid locking the DB and disk I/O errors
        chunk_size = 5000
        total_deleted = 0
        
        while True:
            # Get IDs to delete
            batch_ids = [r[0] for r in db.session.query(SearchLog.id).filter(
                SearchLog.search_date < cutoff_date
            ).limit(chunk_size).all()]
            
            if not batch_ids:
                break
                
            # Delete batch
            SearchLog.query.filter(SearchLog.id.in_(batch_ids)).delete(synchronize_session=False)
            db.session.commit()
            total_deleted += len(batch_ids)
            
            # Small pause
            time.sleep(0.1)
            
        # Log the action
        log_entry = DbMaintenanceLog(
            performed_by=current_user.username,
            action_type='cleanup_search_logs',
            status='success',
            details=json.dumps({
                'cutoff_date': cutoff_date.isoformat(),
                'deleted_count': total_deleted
            })
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f'تم حذف {total_deleted} سجل بحث أقدم من {cutoff_date} بنجاح.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'حدث خطأ أثناء تنظيف سجل البحث: {str(e)}'})

@admin_db_maintenance_bp.route('/admin/db-maintenance/start-repair', methods=['POST'])
@login_required
def start_repair():
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    safe_mode = data.get('safe_mode', True)
    optimize_table = data.get('optimize_table', False)
    
    job_id = f"job_{int(time.time())}"
    with job_lock:
        maintenance_jobs[job_id] = {
            'status': 'pending',
            'progress': 0,
            'message': 'Starting...',
            'created_at': datetime.now().isoformat()
        }
    
    # Start background thread
    app = current_app._get_current_object()
    thread = threading.Thread(target=perform_repair_job, args=(job_id, app, safe_mode, optimize_table, current_user.username))
    thread.start()
    
    return jsonify({'status': 'success', 'job_id': job_id})

@admin_db_maintenance_bp.route('/admin/db-maintenance/status/<job_id>', methods=['GET'])
@login_required
def job_status(job_id):
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    with job_lock:
        job = maintenance_jobs.get(job_id)
    
    if not job:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
        
    return jsonify(job)

@admin_db_maintenance_bp.route('/admin/db-maintenance/cancel/<job_id>', methods=['POST'])
@login_required
def cancel_job(job_id):
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    with job_lock:
        if job_id in maintenance_jobs:
            maintenance_jobs[job_id]['cancelled'] = True
            maintenance_jobs[job_id]['message'] = "Cancelling..."
            
    return jsonify({'status': 'success'})

@admin_db_maintenance_bp.route('/admin/db-maintenance/download-recovery/<job_id>', methods=['GET'])
@login_required
def download_recovery(job_id):
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    with job_lock:
        job = maintenance_jobs.get(job_id)
        
    if not job or 'result' not in job:
        return "Recovery script not found", 404
        
    script_content = job['result'].get('recovery_script', '')
    
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.sql', text=True)
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(script_content)
        
    return send_file(path, as_attachment=True, download_name=f"recovery_script_{job_id}.sql")

@admin_db_maintenance_bp.route('/admin/db-maintenance/undo/<job_id>', methods=['POST'])
@login_required
def undo_job(job_id):
    if not current_user.is_authenticated or session.get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    with job_lock:
        job = maintenance_jobs.get(job_id)
        
    if not job or 'result' not in job:
        return jsonify({'status': 'error', 'message': 'Job result not found'}), 404
        
    script_content = job['result'].get('recovery_script', '')
    if not script_content:
        return jsonify({'status': 'error', 'message': 'No recovery script found'}), 400
        
    try:
        # Execute script
        with db.engine.connect() as conn:
            # Safe way is to split by ';'
            statements = [s.strip() for s in script_content.split(';') if s.strip()]
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
            
        # Log undo
        try:
             log_entry = DbMaintenanceLog(
                performed_by=current_user.username,
                action_type='undo',
                status='success',
                details=json.dumps({'job_id': job_id})
            )
             db.session.add(log_entry)
             db.session.commit()
        except Exception:
            pass

        return jsonify({'status': 'success', 'message': 'Undo completed successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
