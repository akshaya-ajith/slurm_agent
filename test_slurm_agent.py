import unittest
from unittest.mock import patch
import sys
import io
import os

# Import the classes to test
from slurm_interface import ParamikoSlurmClient
from agent import AtomGPTAgent

class TestAtomGPTAgent(unittest.TestCase):
    def setUp(self):
        # Check if API key is present, otherwise skip
        if not os.getenv("ATOMGPT_API_KEY"):
            self.skipTest("ATOMGPT_API_KEY not found in environment")
            
    @patch('builtins.input', return_value='y')
    def test_end_to_end(self, mock_input):
        # This test runs the FULL flow: User Request -> AtomGPT -> Real SLURM -> Output
        # It requires both ATOMGPT_API_KEY and SLURM_PASSWORD in env
        
        if not os.getenv("SLURM_PASSWORD"):
            self.skipTest("SLURM_PASSWORD not found in environment")
            
        print("\n🚀 Starting Full End-to-End Test (Real Connections)...")
        
        # Initialize agent (connects to real SLURM)
        try:
            agent = AtomGPTAgent()
        except SystemExit:
            self.fail("Failed to connect to SLURM (SystemExit)")
            
        # Run a simple job
        # We use a unique string to verify the output matches THIS job
        unique_str = f"Integration_Test_{os.urandom(4).hex()}"
        request = f"Write a job that prints '{unique_str}'"
        
        output = agent.run_job(request)
        
        print(f"\n[Real Job Output]\n{output}\n")
        
        self.assertIsNotNone(output)
        self.assertIn(unique_str, output)




if __name__ == '__main__':
    unittest.main()
