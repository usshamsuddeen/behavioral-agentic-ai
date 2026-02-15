"""
Comprehensive Validation Script
Runs all validation tests and generates complete report
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import time


class ComprehensiveValidator:
    """Runs all validation tests in sequence"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'pending'
        }
        self.backend_path = Path(__file__).parent.parent
    
    def run_sentiment_validation(self):
        """Run sentiment accuracy tests"""
        print("\n" + "="*70)
        print("STEP 1: SENTIMENT ANALYSIS VALIDATION")
        print("="*70)
        
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_sentiment_accuracy.py"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            self.results['tests']['sentiment'] = {
                'status': 'passed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'output': result.stdout,
                'errors': result.stderr
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"ERROR: {e}")
            self.results['tests']['sentiment'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def run_escalation_validation(self):
        """Run escalation accuracy tests"""
        print("\n" + "="*70)
        print("STEP 2: ESCALATION TRIGGER VALIDATION")
        print("="*70)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_escalation_accuracy.py", "-v"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            self.results['tests']['escalation'] = {
                'status': 'passed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'output': result.stdout,
                'errors': result.stderr
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"ERROR: {e}")
            self.results['tests']['escalation'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def run_api_tests(self):
        """Run API tests"""
        print("\n" + "="*70)
        print("STEP 3: API ENDPOINT VALIDATION")
        print("="*70)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_api.py", "-v"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            self.results['tests']['api'] = {
                'status': 'passed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'output': result.stdout,
                'errors': result.stderr
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"ERROR: {e}")
            self.results['tests']['api'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def check_bert_availability(self):
        """Check if BERT model is available"""
        print("\n" + "="*70)
        print("CHECKING BERT MODEL AVAILABILITY")
        print("="*70)
        
        try:
            from app.nlp.transformer_sentiment import is_model_available, get_model_info
            
            available = is_model_available()
            if available:
                info = get_model_info()
                print("[OK] BERT model loaded successfully")
                print(f"   Model: {info.get('model_name', 'unknown')}")
                print(f"   "Languages: {', '.join(info.get('languages_supported', []))}"")
                self.results['bert_available'] = True
                self.results['bert_info'] = info
            else:
                print("[WARNING] BERT model not available - using fallback")
                self.results['bert_available'] = False
            
            return available
            
        except Exception as e:
            print(f"[ERROR] Failed to check BERT: {e}")
            self.results['bert_available'] = False
            self.results['bert_error'] = str(e)
            return False
    
    def generate_summary_report(self):
        """Generate summary validation report"""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY REPORT")
        print("="*70)
        
        print(f"\nTimestamp: {self.results['timestamp']}")
        print(f"BERT Available: {'YES' if self.results.get('bert_available') else 'NO'}")
        
        print("\nTest Results:")
        for test_name, test_result in self.results.get('tests', {}).items():
            status = test_result.get('status', 'unknown')
            emoji = {
                'passed': '[PASS]',
                'failed': '[FAIL]',
                'error': '[ERROR]',
                'unknown': '[?]'
            }.get(status, '[?]')
            print(f"   {emoji} {test_name.upper()}")
        
        # Determine overall status
        all_passed = all(
            t.get('status') == 'passed' 
            for t in self.results.get('tests', {}).values()
        )
        
        if all_passed and self.results.get('bert_available'):
            self.results['overall_status'] = 'passed'
            print("\n[OVERALL STATUS]: ALL TESTS PASSED")
        elif all_passed:
            self.results['overall_status'] = 'passed_no_bert'
            print("\n[OVERALL STATUS]: TESTS PASSED (BERT NOT AVAILABLE)")
        else:
            self.results['overall_status'] = 'failed'
            print("\n[OVERALL STATUS]: SOME TESTS FAILED")
        
        print("="*70)
    
    def save_results(self):
        """Save results to JSON"""
        output_path = self.backend_path / "tests" / "results" / f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n[SAVED] Results saved to: {output_path}")
        return output_path
    
    def run_all(self):
        """Run all validation steps"""
        print("\n"*2)
        print("="*70)
        print("   BEHAVIORAL AGENTIC AI - COMPREHENSIVE VALIDATION")
        print("="*70)
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check BERT first
        self.check_bert_availability()
        
        # Run all tests
        tests_to_run = [
            ('Sentiment Validation', self.run_sentiment_validation),
            ('Escalation Validation', self.run_escalation_validation),
            ('API Validation', self.run_api_tests),
        ]
        
        for test_name, test_func in tests_to_run:
            try:
                test_func()
            except KeyboardInterrupt:
                print(f"\n[INTERRUPTED] {test_name} cancelled by user")
                break
            except Exception as e:
                print(f"\n[ERROR] {test_name} failed: {e}")
                continue
            
            # Small delay between tests
            time.sleep(1)
        
        # Generate summary
        self.generate_summary_report()
        
        # Save results
        output_file = self.save_results()
        
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nValidation complete!")
        
        return self.results


if __name__ == "__main__":
    validator = ComprehensiveValidator()
    results = validator.run_all()
    
    # Exit with appropriate code
    if results['overall_status'] in ['passed', 'passed_no_bert']:
        sys.exit(0)
    else:
        sys.exit(1)
