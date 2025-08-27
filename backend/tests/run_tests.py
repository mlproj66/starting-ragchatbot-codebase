#!/usr/bin/env python3
"""
Test runner for RAG system diagnostics.
Runs all tests and provides comprehensive analysis.
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test_suite(test_file, description):
    """Run a specific test suite and return results"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"File: {test_file}")
    print(f"{'='*60}")
    
    try:
        # Run pytest with verbose output and capture results
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            test_file, 
            '-v', 
            '--tb=short',
            '--disable-warnings'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return {
            'file': test_file,
            'description': description,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'passed': result.returncode == 0
        }
        
    except Exception as e:
        print(f"ERROR running {test_file}: {e}")
        return {
            'file': test_file,
            'description': description,
            'return_code': -1,
            'stdout': '',
            'stderr': str(e),
            'passed': False
        }

def analyze_results(results):
    """Analyze test results and identify issues"""
    print(f"\n{'='*60}")
    print("TEST RESULTS ANALYSIS")
    print(f"{'='*60}")
    
    total_suites = len(results)
    passed_suites = sum(1 for r in results if r['passed'])
    failed_suites = total_suites - passed_suites
    
    print(f"Total test suites: {total_suites}")
    print(f"Passed suites: {passed_suites}")
    print(f"Failed suites: {failed_suites}")
    print()
    
    # Analyze each suite
    issues_found = []
    
    for result in results:
        print(f"Suite: {result['description']}")
        print(f"Status: {'PASSED' if result['passed'] else 'FAILED'}")
        
        if not result['passed']:
            print(f"Return code: {result['return_code']}")
            issues_found.append(result)
            
            # Extract specific error information
            if 'ImportError' in result['stderr'] or 'ModuleNotFoundError' in result['stderr']:
                print("  Issue: Missing Python packages")
            elif 'AssertionError' in result['stdout'] or 'assert' in result['stdout']:
                print("  Issue: Logic/functionality problems")
            elif 'Connection' in result['stderr'] or 'API' in result['stderr']:
                print("  Issue: External service connectivity")
            elif 'Permission' in result['stderr']:
                print("  Issue: File/directory permissions")
            else:
                print("  Issue: Unknown error type")
        
        print()
    
    return issues_found

def generate_recommendations(issues):
    """Generate recommendations based on identified issues"""
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    if not issues:
        print("✅ All tests passed! No issues detected.")
        return
    
    common_issues = []
    
    for issue in issues:
        output_text = issue['stdout'] + issue['stderr']
        
        # Check for API key issues
        if 'ANTHROPIC_API_KEY' in output_text or 'api' in output_text.lower():
            common_issues.append("API_KEY")
        
        # Check for import issues
        if 'ImportError' in output_text or 'ModuleNotFoundError' in output_text:
            common_issues.append("MISSING_PACKAGES")
        
        # Check for database issues
        if 'chroma' in output_text.lower() or 'database' in output_text.lower():
            common_issues.append("DATABASE")
        
        # Check for tool issues
        if 'tool' in output_text.lower():
            common_issues.append("TOOLS")
    
    unique_issues = set(common_issues)
    
    if 'API_KEY' in unique_issues:
        print("\n🔑 API KEY ISSUES:")
        print("  1. Check that ANTHROPIC_API_KEY is set in .env file")
        print("  2. Verify the API key is valid and not a placeholder")
        print("  3. Ensure .env file is in the backend directory")
    
    if 'MISSING_PACKAGES' in unique_issues:
        print("\n📦 PACKAGE ISSUES:")
        print("  1. Install missing packages: pip install anthropic chromadb sentence-transformers")
        print("  2. Check Python version compatibility")
        print("  3. Consider using virtual environment")
    
    if 'DATABASE' in unique_issues:
        print("\n🗄️ DATABASE ISSUES:")
        print("  1. Check ChromaDB permissions and path")
        print("  2. Verify course data is loaded")
        print("  3. Clear and rebuild database if corrupted")
    
    if 'TOOLS' in unique_issues:
        print("\n🔧 TOOL ISSUES:")
        print("  1. Verify tool registration in RAGSystem")
        print("  2. Check tool definition format")
        print("  3. Test tool execution separately")
    
    print(f"\n📊 NEXT STEPS:")
    print("  1. Address the issues above in order of priority")
    print("  2. Re-run the diagnostic tests after each fix")
    print("  3. Test the full system with a simple query")
    print("  4. Check application logs for runtime errors")

def main():
    """Main test runner"""
    print("RAG SYSTEM COMPREHENSIVE TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test suites
    test_suites = [
        ('test_infrastructure.py', 'Infrastructure & Dependencies'),
        ('test_course_search_tool.py', 'CourseSearchTool Unit Tests'),
        ('test_ai_generator.py', 'AIGenerator Unit Tests'),
        ('test_rag_system.py', 'RAGSystem Integration Tests'),
        ('test_diagnostics.py', 'System Diagnostics')
    ]
    
    results = []
    
    # Run each test suite
    for test_file, description in test_suites:
        result = run_test_suite(test_file, description)
        results.append(result)
    
    # Analyze results
    issues = analyze_results(results)
    
    # Generate recommendations
    generate_recommendations(issues)
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'test_results_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return exit code based on results
    return 0 if all(r['passed'] for r in results) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)