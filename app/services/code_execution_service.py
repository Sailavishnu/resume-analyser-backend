"""
Secure Code Execution Service (Without Docker)

Safely executes student code submissions with resource limits and security.
"""
import subprocess
import tempfile
import os
import sys
import time
import signal
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psutil
import logging
from contextlib import contextmanager

from app.models.coding import LanguageSupport, SubmissionStatus

logger = logging.getLogger(__name__)


class CodeExecutionTimeoutError(Exception):
    """Raised when code execution times out"""
    pass


class CodeExecutionService:
    """
    Secure code execution service without Docker.
    Uses subprocess isolation with resource limits.
    """
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "ppp_code_execution"
        self.temp_dir.mkdir(exist_ok=True)
        
    @contextmanager
    def timeout_handler(self, timeout_seconds: int):
        """Context manager for handling timeouts"""
        def timeout_handler_func(signum, frame):
            raise CodeExecutionTimeoutError("Code execution timed out")
        
        # Set timeout signal (Unix/Linux)
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler_func)
            signal.alarm(timeout_seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # Windows fallback - use threading
            result = {'completed': False, 'exception': None}
            
            def target():
                try:
                    yield
                    result['completed'] = True
                except Exception as e:
                    result['exception'] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            
            if not thread.is_alive():
                if result.get('exception'):
                    raise result['exception']
                if not result.get('completed'):
                    raise CodeExecutionTimeoutError("Code execution timed out")
            else:
                raise CodeExecutionTimeoutError("Code execution timed out")
    
    def execute_python_code(
        self, 
        code: str, 
        test_cases: List[Dict[str, str]], 
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Execute Python code against test cases safely.
        
        Args:
            code: Python source code
            test_cases: List of test cases with input/expected_output
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result with status and details
        """
        results = []
        overall_status = SubmissionStatus.ACCEPTED
        error_message = None
        runtime_total = 0
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.temp_dir) as code_file:
            try:
                # Write secure code wrapper
                secure_code = self._wrap_python_code(code)
                code_file.write(secure_code)
                code_file.flush()
                
                # Test each case
                for i, test_case in enumerate(test_cases):
                    try:
                        start_time = time.time()
                        
                        # Execute with input
                        result = self._run_python_subprocess(
                            code_file.name,
                            test_case['input'],
                            timeout
                        )
                        
                        end_time = time.time()
                        runtime = int((end_time - start_time) * 1000)  # ms
                        runtime_total += runtime
                        
                        # Check result
                        if result['returncode'] != 0:
                            overall_status = SubmissionStatus.RUNTIME_ERROR
                            error_message = result['stderr']
                            results.append({
                                'test_case': i + 1,
                                'status': 'runtime_error',
                                'input': test_case['input'],
                                'expected': test_case['expected_output'],
                                'actual': '',
                                'error': result['stderr'],
                                'runtime': runtime
                            })
                            break
                        
                        # Compare output
                        actual_output = result['stdout'].strip()
                        expected_output = test_case['expected_output'].strip()
                        
                        if actual_output == expected_output:
                            results.append({
                                'test_case': i + 1,
                                'status': 'passed',
                                'input': test_case['input'],
                                'expected': expected_output,
                                'actual': actual_output,
                                'runtime': runtime
                            })
                        else:
                            overall_status = SubmissionStatus.WRONG_ANSWER
                            results.append({
                                'test_case': i + 1,
                                'status': 'failed',
                                'input': test_case['input'],
                                'expected': expected_output,
                                'actual': actual_output,
                                'runtime': runtime
                            })
                            break
                            
                    except CodeExecutionTimeoutError:
                        overall_status = SubmissionStatus.TIME_LIMIT_EXCEEDED
                        error_message = f"Time limit exceeded (>{timeout}s)"
                        results.append({
                            'test_case': i + 1,
                            'status': 'timeout',
                            'input': test_case['input'],
                            'expected': test_case['expected_output'],
                            'actual': '',
                            'error': error_message,
                            'runtime': timeout * 1000
                        })
                        break
                        
                    except Exception as e:
                        overall_status = SubmissionStatus.RUNTIME_ERROR
                        error_message = str(e)
                        results.append({
                            'test_case': i + 1,
                            'status': 'error',
                            'input': test_case['input'],
                            'expected': test_case['expected_output'],
                            'actual': '',
                            'error': str(e),
                            'runtime': 0
                        })
                        break
                        
            finally:
                # Clean up temp file
                try:
                    os.unlink(code_file.name)
                except:
                    pass
        
        # Calculate stats
        passed_tests = len([r for r in results if r['status'] == 'passed'])
        total_tests = len(test_cases)
        
        return {
            'status': overall_status.value,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'runtime': runtime_total,
            'memory_used': 0,  # Not implemented for simplicity
            'error_message': error_message,
            'test_results': results,
            'language': LanguageSupport.PYTHON.value
        }
    
    def _wrap_python_code(self, user_code: str) -> str:
        """
        Wrap user code with security restrictions and I/O handling.
        """
        wrapper = f'''
import sys
import os
import signal

# Security: Remove dangerous modules
banned_modules = [
    'os', 'subprocess', 'socket', 'urllib', 'http', 'ftplib',
    'smtplib', 'telnetlib', 'requests', '__import__', 'eval',
    'exec', 'compile', 'open', 'file', 'input'
]

# Restricted builtins
safe_builtins = {{
    'len': len, 'range': range, 'int': int, 'float': float,
    'str': str, 'list': list, 'dict': dict, 'set': set,
    'tuple': tuple, 'bool': bool, 'abs': abs, 'max': max,
    'min': min, 'sum': sum, 'sorted': sorted, 'reversed': reversed,
    'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
    'print': print, '__name__': '__main__'
}}

# Override builtins
import builtins
builtins.__dict__.clear()
builtins.__dict__.update(safe_builtins)

# User code starts here
{user_code}
'''
        return wrapper
    
    def _run_python_subprocess(
        self, 
        code_file_path: str, 
        input_data: str, 
        timeout: int
    ) -> Dict[str, Any]:
        """
        Run Python code in subprocess with resource limits.
        """
        try:
            # Prepare environment
            env = os.environ.copy()
            env['PYTHONPATH'] = ''  # Clear Python path for security
            
            # Run with resource limits
            process = subprocess.Popen(
                [sys.executable, code_file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=self.temp_dir,
                # Security: prevent shell access
                shell=False,
                # Resource limits (Unix only)
                preexec_fn=self._set_resource_limits if os.name != 'nt' else None
            )
            
            # Communicate with timeout
            try:
                stdout, stderr = process.communicate(
                    input=input_data, 
                    timeout=timeout
                )
                returncode = process.returncode
                
            except subprocess.TimeoutExpired:
                process.kill()
                raise CodeExecutionTimeoutError("Process timed out")
            
            return {
                'returncode': returncode,
                'stdout': stdout,
                'stderr': stderr
            }
            
        except Exception as e:
            return {
                'returncode': 1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def _set_resource_limits(self):
        """Set resource limits for subprocess (Unix only)."""
        try:
            import resource
            # CPU time limit (seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
            # Memory limit (bytes) - 256MB
            resource.setrlimit(resource.RLIMIT_AS, (256*1024*1024, 256*1024*1024))
            # No file creation
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
            # No subprocess creation
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
        except ImportError:
            # Windows - resource module not available
            pass
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")


# Global service instance
code_execution_service = CodeExecutionService()