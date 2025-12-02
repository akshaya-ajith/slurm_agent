import time
import random
import paramiko
from abc import ABC, abstractmethod
from typing import Dict, Any

class SlurmClient(ABC):
    """Abstract base class for SLURM interactions."""
    
    @abstractmethod
    def submit_job(self, script_content: str) -> str:
        """Submits a SLURM job script and returns the Job ID."""
        pass

    @abstractmethod
    def get_job_status(self, job_id: str) -> str:
        """Returns the status of the job (PENDING, RUNNING, COMPLETED, FAILED)."""
        pass

    @abstractmethod
    def get_job_output(self, job_id: str) -> str:
        """Returns the stdout/stderr of the job."""
        pass

class MockSlurmClient(SlurmClient):
    """Simulates a SLURM cluster for development."""
    
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        print("🔧 Initialized MockSlurmClient")

    def submit_job(self, script_content: str) -> str:
        job_id = str(random.randint(1000, 9999))
        self.jobs[job_id] = {
            "status": "PENDING",
            "script": script_content,
            "submitted_at": time.time(),
            "output": ""
        }
        print(f"🚀 [Mock] Job submitted! ID: {job_id}")
        return job_id

    def get_job_status(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return "UNKNOWN"
        
        job = self.jobs[job_id]
        # Simulate progression: PENDING -> RUNNING -> COMPLETED
        elapsed = time.time() - job["submitted_at"]
        
        if elapsed < 2:
            status = "PENDING"
        elif elapsed < 5:
            status = "RUNNING"
        else:
            status = "COMPLETED"
            # Generate fake output based on script content (simple heuristic)
            if not job["output"]:
                if "python" in job["script"]:
                    job["output"] = "Result: 42 (Mock Output)"
                else:
                    job["output"] = "Job completed successfully."
        
        job["status"] = status
        return status

    def get_job_output(self, job_id: str) -> str:
        return self.jobs.get(job_id, {}).get("output", "No output available.")

class ParamikoSlurmClient(SlurmClient):
    """Actual SLURM client using SSH via Paramiko."""
    
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sftp = None
        self.job_files = {} # Map job_id -> output_filename_pattern
        print(f"🔌 Initialized ParamikoSlurmClient for {user}@{host}")

    def connect(self):
        """Establishes the SSH connection."""
        try:
            self.client.connect(self.host, username=self.user, password=self.password, timeout=10)
            self.sftp = self.client.open_sftp()
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def _run_command(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        return exit_status, stdout.read().decode().strip(), stderr.read().decode().strip()

    def submit_job(self, script_content: str) -> str:
        # 1. Create a remote script file using SFTP
        filename = f"job_{int(time.time())}.sh"
        
        try:
            with self.sftp.file(filename, 'w') as f:
                f.write(script_content)
        except Exception as e:
            raise Exception(f"Failed to upload script via SFTP: {e}")
        
        # 2. Submit via sbatch
        # sbatch output format: "Submitted batch job 123456"
        code, out, err = self._run_command(f"sbatch {filename}")
        
        if code != 0:
            raise Exception(f"sbatch failed: {err}")
            
        # Parse Job ID
        # Expected output: "Submitted batch job 123456"
        try:
            job_id = out.split()[-1]
        except IndexError:
             raise Exception(f"Could not parse job ID from sbatch output: {out}")

        # Parse output filename from script
        # Look for #SBATCH --output=...
        output_pattern = "slurm-%j.out" # Default
        for line in script_content.splitlines():
            if line.strip().startswith("#SBATCH --output="):
                output_pattern = line.strip().split("=")[1]
                break
        
        self.job_files[job_id] = output_pattern
        print(f"🚀 Job submitted! ID: {job_id} (Output: {output_pattern})")
        return job_id

    def get_job_status(self, job_id: str) -> str:
        # squeue -j <id> -h -o %T (Returns state like PENDING, RUNNING, COMPLETED)
        # Note: If job is finished, squeue might return nothing.
        code, out, err = self._run_command(f"squeue -j {job_id} -h -o %T")
        
        if not out:
            # Check sacct for completed jobs to be sure
            # sacct -j <id> -n -o State
            code_sacct, out_sacct, err_sacct = self._run_command(f"sacct -j {job_id} -n -o State")
            if out_sacct:
                return out_sacct.split()[0].strip() # Take the first word (e.g. COMPLETED)
            
            # Fallback: assume completed if not in queue
            return "COMPLETED" 
            
        return out.strip()

    def get_job_output(self, job_id: str) -> str:
        # Determine output filename
        pattern = self.job_files.get(job_id, "slurm-%j.out")
        outfile = pattern.replace("%j", job_id)
        
        # Retry loop to wait for file to appear (filesystem latency)
        max_retries = 10
        for i in range(max_retries):
            try:
                # Try to read via SFTP first (cleaner)
                with self.sftp.file(outfile, 'r') as f:
                    return f.read().decode()
            except IOError:
                # File might not exist yet or SFTP failed
                # Try cat as fallback
                code, out, err = self._run_command(f"cat {outfile}")
                if code == 0:
                    return out
            
            # If we are here, both failed. Wait and retry.
            if i < max_retries - 1:
                time.sleep(3)
                
        return f"Output file {outfile} not found after retries."
