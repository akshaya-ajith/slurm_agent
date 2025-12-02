import os
import sys
import time
import getpass
from dotenv import load_dotenv
from openai import OpenAI
from slurm_interface import ParamikoSlurmClient

# Load environment variables
load_dotenv()

# Configuration
HOST = "atomgptlab01.wse.jhu.edu"
USER = "aajith1"
MODEL = "openai/gpt-oss-20b"

class AtomGPTAgent:
    def __init__(self):
        print("🤖 Initializing AtomGPT Agent...")
        
        # 1. Setup OpenAI (AtomGPT)
        api_key = os.getenv("ATOMGPT_API_KEY")
        if not api_key:
            print("⚠️ ATOMGPT_API_KEY not found in environment.")
            api_key = getpass.getpass("🔑 Please enter your AtomGPT API Key: ")
        
        self.ai_client = OpenAI(
            base_url="https://atomgpt.org/api",
            api_key=api_key
        )
        
        # 2. Setup SLURM Connection
        print(f"🔌 Connecting to SLURM at {USER}@{HOST}...")
        password = os.getenv("SLURM_PASSWORD")
        if not password:
            password = getpass.getpass(f"🔑 Please enter SSH password for {USER}@{HOST}: ")
        
        self.slurm = ParamikoSlurmClient(HOST, USER, password)
        if not self.slurm.connect():
            print("❌ Failed to connect to SLURM cluster. Exiting.")
            sys.exit(1)
            
        print("✅ Connected to SLURM!")

    def generate_script(self, user_request: str) -> str:
        """
        Uses OpenAI to generate a SLURM script based on the user request.
        """
        print(f"🧠 Thinking about: '{user_request}'...")
        
        system_prompt = """You are an expert HPC engineer. 
        Your goal is to write a valid SLURM job script (bash) based on the user's request.
        
        Rules:
        1. First, provide a brief "Reasoning:" section explaining your approach.
        2. Then, provide the bash script in a markdown code block (```bash ... ```).
        3. Include standard #SBATCH directives (job-name, output, time).
        4. Default to --time=00:05:00 unless specified.
        5. If the user asks for python code, use `python3 -c "..."` or create a here-doc.
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_request}
                ],
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            
            # Extract reasoning and script
            reasoning = "No reasoning provided."
            script = ""
            
            if "Reasoning:" in content:
                parts = content.split("```", 1)
                reasoning = parts[0].replace("Reasoning:", "").strip()
                if len(parts) > 1:
                    script = "```" + parts[1]
            else:
                script = content

            print(f"🤔 Agent Reasoning: {reasoning}")

            # Clean up markdown if present
            if "```bash" in script:
                script = script.split("```bash")[1].split("```")[0].strip()
            elif "```" in script:
                script = script.split("```")[1].split("```")[0].strip()
                
            return script
        except Exception as e:
            print(f"❌ OpenAI Error: {e}")
            return ""

    def run_job(self, user_request: str):
        print(f"\n--- Processing Request: {user_request} ---")
        
        # 1. Generate Script
        script = self.generate_script(user_request)
        if not script:
            return None

        print(f"📝 Generated Script:\n{'-'*20}\n{script}\n{'-'*20}")
        
        confirm = input("❓ Submit this job? (y/n): ")
        if confirm.lower() != 'y':
            print("🚫 Cancelled.")
            return None

        # 2. Submit Job
        try:
            job_id = self.slurm.submit_job(script)
        except Exception as e:
            print(f"❌ Submission Failed: {e}")
            return None
        
        # 3. Monitor Job
        print(f"⏳ Monitoring Job {job_id}...")
        try:
            while True:
                status = self.slurm.get_job_status(job_id)
                print(f"   Status: {status}")
                if status in ["COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"]:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring interrupted by user. Job is likely still running.")
            return None
            
        # 4. Get Results
        if status == "COMPLETED":
            print("\n🎉 Job Finished! Output:")
            output = self.slurm.get_job_output(job_id)
            print(f"{'-'*20}\n{output}\n{'-'*20}")
            return output
        else:
            print(f"❌ Job finished with status: {status}")
            return None

if __name__ == "__main__":
    try:
        agent = AtomGPTAgent()
        
        while True:
            try:
                req = input("\n🤖 What job would you like to run? (or 'exit'): ")
                if req.lower() in ['exit', 'quit']:
                    break
                if not req.strip():
                    continue
                agent.run_job(req)
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
