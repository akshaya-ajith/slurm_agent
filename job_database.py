"""
Job History Database for SLURM Agent.
Tracks all submitted jobs with their requests, scripts, status, and outputs.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class JobDatabase:
    """SQLite-based job tracking database."""
    
    def __init__(self, db_path: str = "jobs.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self._create_tables()
    
    def _create_tables(self):
        """Create the jobs table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                request TEXT NOT NULL,
                script TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                output TEXT,
                submitted_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                resources TEXT
            )
        """)
        self.conn.commit()
    
    def add_job(
        self, 
        job_id: str, 
        request: str, 
        script: str, 
        resources: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a new job to the database.
        
        Args:
            job_id: SLURM job ID
            request: Original user request text
            script: Generated SLURM script content
            resources: Optional dict with cores, mem, time info
        """
        self.conn.execute(
            """INSERT INTO jobs 
               (job_id, request, script, status, submitted_at, resources)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                request,
                script,
                "PENDING",
                datetime.now().isoformat(),
                json.dumps(resources) if resources else None
            )
        )
        self.conn.commit()
    
    def update_job(
        self, 
        job_id: str, 
        status: str, 
        output: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """
        Update job status and optionally output/completion time.
        
        Args:
            job_id: SLURM job ID to update
            status: New status (PENDING, RUNNING, COMPLETED, FAILED, etc.)
            output: Job stdout/stderr content
            completed_at: When the job completed
        """
        if completed_at is None and status in ["COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"]:
            completed_at = datetime.now()
        
        self.conn.execute(
            """UPDATE jobs 
               SET status = ?, output = ?, completed_at = ?
               WHERE job_id = ?""",
            (
                status,
                output,
                completed_at.isoformat() if completed_at else None,
                job_id
            )
        )
        self.conn.commit()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by its ID.
        
        Returns:
            Dict with job data or None if not found
        """
        cursor = self.conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all jobs with a specific status.
        
        Args:
            status: Status to filter by (PENDING, RUNNING, COMPLETED, etc.)
            
        Returns:
            List of job dicts
        """
        cursor = self.conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY submitted_at DESC",
            (status,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs that are still running (PENDING or RUNNING)."""
        cursor = self.conn.execute(
            """SELECT * FROM jobs 
               WHERE status IN ('PENDING', 'RUNNING') 
               ORDER BY submitted_at DESC"""
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dicts, newest first
        """
        cursor = self.conn.execute(
            "SELECT * FROM jobs ORDER BY submitted_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_script(self, job_id: str) -> Optional[str]:
        """Get the script content for a specific job."""
        job = self.get_job(job_id)
        return job["script"] if job else None
    
    def find_similar_jobs(self, request: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find jobs with similar request text (simple keyword matching).
        
        This is a basic implementation using LIKE queries.
        Could be enhanced with proper text search or embeddings later.
        
        Args:
            request: Request text to search for
            limit: Maximum number of results
            
        Returns:
            List of similar job dicts
        """
        # Extract keywords (simple: split on whitespace, filter short words)
        keywords = [w.lower() for w in request.split() if len(w) > 3]
        
        if not keywords:
            return []
        
        # Build LIKE clause for each keyword
        conditions = " OR ".join(["LOWER(request) LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        params.append(limit)
        
        cursor = self.conn.execute(
            f"""SELECT * FROM jobs 
                WHERE {conditions}
                ORDER BY submitted_at DESC 
                LIMIT ?""",
            params
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
