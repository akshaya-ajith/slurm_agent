import getpass
import time
from slurm_interface import ParamikoSlurmClient

HOST = "atomgptlab01.wse.jhu.edu"
USER = "aajith1"

def main():
    print(f"--- SLURM SSH Demo: Add Two Numbers ---")
    password = getpass.getpass(f"Enter password for {USER}@{HOST}: ")
    
    client = ParamikoSlurmClient(HOST, USER, password)
    if not client.connect():
        return

    # The python code we want to run on the cluster
    # We print the hostname to PROVE it ran on the remote machine
    python_code = "import socket; print(f'Hello from {socket.gethostname()}! The sum of 50 + 50 is {50+50}')"
    
    # The SLURM script that wraps the python code
    slurm_script = f"""#!/bin/bash
#SBATCH --job-name=test_add
#SBATCH --output=slurm-%j.out
#SBATCH --time=00:01:00

python3 -c "{python_code}"
"""
    
    print("\nSubmitting Job...")
    try:
        job_id = client.submit_job(slurm_script)
        print(f"Waiting for Job {job_id} to complete...")
        
        while True:
            status = client.get_job_status(job_id)
            print(f"Status: {status}")
            if status in ["COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"]:
                break
            time.sleep(2)
            
        if status == "COMPLETED":
            print("\n--- Job Output ---")
            output = client.get_job_output(job_id)
            print(output)
            if "100" in output:
                print("\n✅ SUCCESS: Calculated 50+50=100")
            else:
                print("\n⚠️ Output unexpected.")
        else:
            print(f"❌ Job finished with status: {status}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
