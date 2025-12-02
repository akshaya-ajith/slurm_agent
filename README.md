# atomGPT SLURM Agent

An agentic tool that uses OpenAI to generate and submit SLURM jobs to the `atomgptlab01` HPC cluster via SSH.

## Features
- **Natural Language Interface**: Ask for jobs in plain English (e.g., "Run a python script to train a model").
- **Automatic Script Generation**: Uses GPT-4o to write valid Bash/SLURM scripts.
- **SSH Integration**: Securely connects to the cluster using `paramiko`.
- **Job Monitoring**: Automatically tracks job status and retrieves output.

## Prerequisites
- Python 3.8+
- SSH access to `atomgptlab01.wse.jhu.edu`
- OpenAI API Key

## Installation
1. Install dependencies:
   ```bash
   pip install openai paramiko
   ```

## Usage
Run the agent:
```bash
python3 agent.py
```

You will be prompted for:
1. **OpenAI API Key**: To power the agent's logic.
2. **SSH Password**: To connect to the cluster.

## Project Structure
- `agent.py`: Main entry point. Handles user interaction and AI logic.
- `slurm_interface.py`: Handles low-level SSH and SLURM commands (`sbatch`, `squeue`).
- `ssh_demo.py`: Simple script to verify SSH connectivity and job submission.
- `discover_slurm.py`: Utility to check for SLURM API availability.

## Configuration
Currently, keys and passwords are entered at runtime for security.
