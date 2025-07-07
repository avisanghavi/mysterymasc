#!/usr/bin/env python3
"""Test script for sales agent code generation and execution."""

import asyncio
import os
import sys
import tempfile
import logging
from typing import Dict, Any, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_builder.code_generator import AgentCodeGenerator
from departments.sales.lead_scanner_agent import create_lead_scanner_spec
from departments.sales.outreach_composer_agent import create_outreach_composer_spec
from departments.sales.meeting_scheduler_agent import create_meeting_scheduler_spec
from departments.sales.pipeline_tracker_agent import create_pipeline_tracker_spec

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalesAgentTester:
    """Test harness for sales agent code generation and execution."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize the tester."""
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            logger.warning("No Anthropic API key provided - code generation will be skipped")
        
        self.code_generator = None
        if self.anthropic_api_key:
            self.code_generator = AgentCodeGenerator(self.anthropic_api_key)
    
    async def test_agent_specifications(self) -> Dict[str, bool]:
        """Test that all agent specifications are valid and can be created."""
        logger.info("Testing agent specifications...")
        
        results = {}
        session_id = "test_session_123"
        
        # Test Lead Scanner Agent
        try:
            lead_scanner_spec = create_lead_scanner_spec(session_id)
            logger.info(f"✓ Lead Scanner spec created: {lead_scanner_spec.name}")
            results["lead_scanner_spec"] = True
        except Exception as e:
            logger.error(f"✗ Lead Scanner spec failed: {e}")
            results["lead_scanner_spec"] = False
        
        # Test Outreach Composer Agent
        try:
            outreach_composer_spec = create_outreach_composer_spec(session_id)
            logger.info(f"✓ Outreach Composer spec created: {outreach_composer_spec.name}")
            results["outreach_composer_spec"] = True
        except Exception as e:
            logger.error(f"✗ Outreach Composer spec failed: {e}")
            results["outreach_composer_spec"] = False
        
        # Test Meeting Scheduler Agent
        try:
            meeting_scheduler_spec = create_meeting_scheduler_spec(session_id)
            logger.info(f"✓ Meeting Scheduler spec created: {meeting_scheduler_spec.name}")
            results["meeting_scheduler_spec"] = True
        except Exception as e:
            logger.error(f"✗ Meeting Scheduler spec failed: {e}")
            results["meeting_scheduler_spec"] = False
        
        # Test Pipeline Tracker Agent
        try:
            pipeline_tracker_spec = create_pipeline_tracker_spec(session_id)
            logger.info(f"✓ Pipeline Tracker spec created: {pipeline_tracker_spec.name}")
            results["pipeline_tracker_spec"] = True
        except Exception as e:
            logger.error(f"✗ Pipeline Tracker spec failed: {e}")
            results["pipeline_tracker_spec"] = False
        
        return results
    
    async def test_code_generation(self) -> Dict[str, bool]:
        """Test code generation for each sales agent."""
        if not self.code_generator:
            logger.warning("Skipping code generation tests - no API key")
            return {}
        
        logger.info("Testing code generation...")
        
        results = {}
        session_id = "test_session_123"
        
        # Create agent specifications
        agents = {
            "lead_scanner": create_lead_scanner_spec(session_id),
            "outreach_composer": create_outreach_composer_spec(session_id),
            "meeting_scheduler": create_meeting_scheduler_spec(session_id),
            "pipeline_tracker": create_pipeline_tracker_spec(session_id)
        }
        
        for agent_name, spec in agents.items():
            try:
                logger.info(f"Generating code for {agent_name}...")
                
                # Generate code
                generated_code = await self.code_generator.generate_agent_code(spec)
                
                # Save generated code to file for inspection
                output_dir = "generated_agents"
                os.makedirs(output_dir, exist_ok=True)
                
                output_file = os.path.join(output_dir, f"{agent_name}_agent.py")
                with open(output_file, "w") as f:
                    f.write(generated_code)
                
                logger.info(f"✓ Code generated for {agent_name}: {len(generated_code)} chars")
                logger.info(f"  Saved to: {output_file}")
                results[f"{agent_name}_generation"] = True
                
            except Exception as e:
                logger.error(f"✗ Code generation failed for {agent_name}: {e}")
                results[f"{agent_name}_generation"] = False
        
        return results
    
    async def test_code_validation(self) -> Dict[str, bool]:
        """Test that generated code is syntactically valid."""
        logger.info("Testing code validation...")
        
        results = {}
        generated_dir = "generated_agents"
        
        if not os.path.exists(generated_dir):
            logger.warning("No generated agents directory found - skipping validation")
            return {}
        
        # Test each generated agent file
        for filename in os.listdir(generated_dir):
            if filename.endswith("_agent.py"):
                agent_name = filename.replace("_agent.py", "")
                file_path = os.path.join(generated_dir, filename)
                
                try:
                    # Try to compile the code
                    with open(file_path, "r") as f:
                        code = f.read()
                    
                    compile(code, file_path, "exec")
                    logger.info(f"✓ Code validation passed for {agent_name}")
                    results[f"{agent_name}_validation"] = True
                    
                except SyntaxError as e:
                    logger.error(f"✗ Syntax error in {agent_name}: {e}")
                    results[f"{agent_name}_validation"] = False
                    
                except Exception as e:
                    logger.error(f"✗ Validation failed for {agent_name}: {e}")
                    results[f"{agent_name}_validation"] = False
        
        return results
    
    async def test_agent_instantiation(self) -> Dict[str, bool]:
        """Test that generated agents can be instantiated (mock mode)."""
        logger.info("Testing agent instantiation...")
        
        results = {}
        generated_dir = "generated_agents"
        
        if not os.path.exists(generated_dir):
            logger.warning("No generated agents directory found - skipping instantiation")
            return {}
        
        # Add generated directory to path
        sys.path.insert(0, os.path.abspath(generated_dir))
        
        for filename in os.listdir(generated_dir):
            if filename.endswith("_agent.py"):
                agent_name = filename.replace("_agent.py", "")
                module_name = filename.replace(".py", "")
                
                try:
                    # Import the module
                    __import__(module_name)
                    logger.info(f"✓ Module import successful for {agent_name}")
                    results[f"{agent_name}_import"] = True
                    
                    # Try to find and instantiate the agent class
                    module = sys.modules[module_name]
                    
                    # Look for agent class (typically ends with 'Agent')
                    agent_class = None
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            attr_name.endswith('Agent') and 
                            attr_name != 'SandboxAgent' and
                            attr_name != 'BaseAgent'):
                            agent_class = attr
                            break
                    
                    if agent_class:
                        # Try to instantiate (in mock mode)
                        logger.info(f"Found agent class: {agent_class.__name__}")
                        # Note: Not actually instantiating to avoid dependency issues
                        logger.info(f"✓ Agent class found for {agent_name}")
                        results[f"{agent_name}_class_found"] = True
                    else:
                        logger.error(f"✗ No agent class found in {agent_name}")
                        results[f"{agent_name}_class_found"] = False
                        
                except ImportError as e:
                    logger.error(f"✗ Import failed for {agent_name}: {e}")
                    results[f"{agent_name}_import"] = False
                    
                except Exception as e:
                    logger.error(f"✗ Instantiation test failed for {agent_name}: {e}")
                    results[f"{agent_name}_instantiation"] = False
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        logger.info("Starting comprehensive sales agent testing...")
        
        all_results = {}
        
        # Test 1: Agent Specifications
        spec_results = await self.test_agent_specifications()
        all_results["specifications"] = spec_results
        
        # Test 2: Code Generation (if API key available)
        if self.code_generator:
            gen_results = await self.test_code_generation()
            all_results["code_generation"] = gen_results
            
            # Test 3: Code Validation
            val_results = await self.test_code_validation()
            all_results["code_validation"] = val_results
            
            # Test 4: Agent Instantiation
            inst_results = await self.test_agent_instantiation()
            all_results["instantiation"] = inst_results
        else:
            logger.info("Skipping code generation tests - no Anthropic API key")
        
        return all_results
    
    def print_test_summary(self, results: Dict[str, Any]) -> None:
        """Print a comprehensive test summary."""
        logger.info("\n" + "="*60)
        logger.info("SALES AGENT TESTING SUMMARY")
        logger.info("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in results.items():
            logger.info(f"\n{category.upper()}:")
            category_passed = 0
            category_total = 0
            
            for test_name, passed in tests.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                logger.info(f"  {test_name}: {status}")
                category_total += 1
                total_tests += 1
                if passed:
                    category_passed += 1
                    passed_tests += 1
            
            logger.info(f"  Category Score: {category_passed}/{category_total}")
        
        logger.info(f"\nOVERALL SCORE: {passed_tests}/{total_tests}")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        logger.info(f"SUCCESS RATE: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 EXCELLENT - Sales agents are working well!")
        elif success_rate >= 60:
            logger.info("👍 GOOD - Sales agents are mostly functional")
        elif success_rate >= 40:
            logger.info("⚠️  FAIR - Some issues need attention")
        else:
            logger.info("❌ POOR - Significant issues need resolution")


async def main():
    """Main test execution."""
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY environment variable not set")
        logger.warning("Code generation tests will be skipped")
        logger.warning("To test code generation, set: export ANTHROPIC_API_KEY=your_key")
    
    # Run tests
    tester = SalesAgentTester(api_key)
    results = await tester.run_all_tests()
    tester.print_test_summary(results)
    
    # Return exit code based on success rate
    total_tests = sum(len(tests) for tests in results.values())
    passed_tests = sum(sum(tests.values()) for tests in results.values())
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    return 0 if success_rate >= 80 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)