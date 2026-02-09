from slurm_interface import SlurmClient

class SandboxManager:
    """Manages isolated python venv environments for SLURM jobs."""
    
    def __init__(self, slurm_client: SlurmClient, env_base_path: str = "~/.slurm_agent/envs"):
        self.slurm = slurm_client
        self.env_base_path = env_base_path
        
    def _get_env_path(self, name: str) -> str:
        """Returns the full path for a given environment name."""
        return f"{self.env_base_path}/{name}"

    def list_sandboxes(self):
        """List available venv environments."""
        # Just list directories in the base path
        # Use source ~/.bashrc to be safe, though ls usually works without it.
        # But we want consistent environment.
        cmd = f"source ~/.bashrc && ls -1 {self.env_base_path}"
        code, out, err = self.slurm._run_command(cmd)
        if code != 0:
            return []
            
        envs = []
        for line in out.splitlines():
            name = line.strip()
            if name:
                envs.append(name)
        return envs

    def ensure_sandbox(self, name: str, packages: list) -> bool:
        """
        Ensures a sandbox with the given name exists.
        If it doesn't exist, it creates it and installs the packages.
        """
        print(f"Checking for sandbox '{name}'...")
        env_path = self._get_env_path(name)
        
        # Verify existence via execution
        # Check if the python binary exists and is executable
        check_cmd = f"source ~/.bashrc && test -x {env_path}/bin/python"
        code, _, _ = self.slurm._run_command(check_cmd)
        
        if code == 0:
            print(f"✅ Sandbox '{name}' already exists.")
            if packages:
                print(f"Ensuring packages in '{name}': {', '.join(packages)}")
                self.install_packages(name, packages)
            return True
            
        print(f"⚠️ Sandbox '{name}' not found (or broken). Creating...")
        return self.create_sandbox(name, packages)

    def create_sandbox(self, name: str, packages: list) -> bool:
        """Create a new venv environment and install packages."""
        print(f"🔨 Creating venv '{name}'...")
        env_path = self._get_env_path(name)
        
        # Ensure parent dir exists
        cmd_mkdir = f"source ~/.bashrc && mkdir -p {self.env_base_path}"
        self.slurm._run_command(cmd_mkdir)
        
        # Create venv
        cmd = f"source ~/.bashrc && python3 -m venv {env_path}"
        code, out, err = self.slurm._run_command(cmd)
        
        if code != 0:
            print(f"❌ Failed to create sandbox '{name}':")
            print(f"   STDOUT: {out}")
            print(f"   STDERR: {err}")
            return False
            
        # Install packages
        if packages:
            return self.install_packages(name, packages)
            
        return True

    def install_packages(self, name: str, packages: list) -> bool:
        """Install packages into a specific sandbox."""
        print(f"⬇️ Installing packages in '{name}': {', '.join(packages)}")
        env_path = self._get_env_path(name)
        
        pkgs_str = " ".join(packages)
        # Use the pip specific to the venv
        cmd = f"source ~/.bashrc && {env_path}/bin/pip install {pkgs_str}"
        
        code, out, err = self.slurm._run_command(cmd)
        if code == 0:
            print(f"✅ Packages installed in '{name}'")
            return True
        else:
            print(f"❌ Failed to install packages in '{name}':")
            print(f"   STDOUT: {out}")
            print(f"   STDERR: {err}")
            return False

    def wrap_job_script(self, script: str, sandbox_name: str) -> str:
        """
        Injects venv activation into a SLURM script.
        """
        lines = script.splitlines()
        new_lines = []
        
        # Find the last #SBATCH directive
        last_sbatch_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#SBATCH"):
                last_sbatch_idx = i
        
        # If no SBATCH, check for shebang
        insert_idx = 0
        if last_sbatch_idx >= 0:
            insert_idx = last_sbatch_idx + 1
        elif lines and lines[0].startswith("#!"):
            insert_idx = 1
            
        env_path = self._get_env_path(sandbox_name)
        activation_block = [
            "",
            "# --- Sandbox Activation ---",
            f"source {env_path}/bin/activate",
            f"echo '✅ Activated sandbox: {sandbox_name}'",
            "# --------------------------",
            ""
        ]
        
        new_lines = lines[:insert_idx] + activation_block + lines[insert_idx:]
        return "\n".join(new_lines)
