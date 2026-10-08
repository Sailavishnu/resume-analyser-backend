#!/usr/bin/env python3
"""
Core Backend Test Script

Tests the essential coding platform functionality without ML dependencies.
"""
import asyncio
import sys
from datetime import datetime

async def test_basic_imports():
    """Test basic imports without database connection."""
    print("Testing basic imports...")
    
    try:
        # Test core models
        from app.models.coding import CodingProblem, CodeSubmission, CodingStats
        print("✓ Core models imported successfully")
        
        # Test services (without initialization)
        from app.services.analytics_service import AnalyticsService
        from app.services.leaderboard_service import LeaderboardService
        from app.services.code_execution_service import CodeExecutionService
        print("✓ Services imported successfully")
        
        # Test API modules (without actual endpoints)
        from app.api import coding
        print("✓ API modules imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

async def test_code_execution():
    """Test code execution service."""
    print("\nTesting code execution service...")
    
    try:
        from app.services.code_execution_service import code_execution_service
        
        # Test simple Python code
        test_code = """
def solution():
    return [1, 2, 3, 4, 5]

result = solution()
print(result)
"""
        
        result = await code_execution_service.execute_code(
            code=test_code,
            language="python",
            timeout=5.0
        )
        
        if result["status"] == "success":
            print("✓ Code execution service working")
            return True
        else:
            print(f"✗ Code execution failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ Code execution test error: {e}")
        return False

async def test_models():
    """Test model creation and validation."""
    print("\nTesting model creation...")
    
    try:
        from app.models.coding import CodingProblem, DifficultyLevel, ProblemCategory
        
        # Test problem creation
        problem = CodingProblem(
            problem_id="test_001",
            title="Two Sum",
            description="Find two numbers that add up to target",
            difficulty=DifficultyLevel.EASY,
            category=ProblemCategory.ARRAYS,
            examples=[
                {
                    "input": "[2,7,11,15], target=9",
                    "output": "[0,1]",
                    "explanation": "nums[0] + nums[1] = 2 + 7 = 9"
                }
            ],
            constraints="1 <= nums.length <= 10^4",
            tags=["array", "hash-table"],
            solution_template="def two_sum(nums, target):",
            test_cases=[
                {
                    "input": {"nums": [2, 7, 11, 15], "target": 9},
                    "expected_output": [0, 1],
                    "is_example": True
                }
            ],
            hints=["Use a hash table to store indices"],
            time_complexity="O(n)",
            space_complexity="O(n)",
            xp_reward=10
        )
        
        print("✓ CodingProblem model created successfully")
        print(f"  - Problem: {problem.title}")
        print(f"  - Difficulty: {problem.difficulty}")
        print(f"  - XP Reward: {problem.xp_reward}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model creation error: {e}")
        return False

def test_frontend_build():
    """Test if frontend can be built (check package.json)."""
    print("\nTesting frontend setup...")
    
    try:
        import os
        import json
        
        frontend_path = "../frontend"
        package_json_path = os.path.join(frontend_path, "package.json")
        
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            required_deps = [
                "react", "react-dom", "react-router-dom",
                "@monaco-editor/react", "zustand", "recharts"
            ]
            
            missing_deps = []
            for dep in required_deps:
                if dep not in package_data.get("dependencies", {}):
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"✗ Missing frontend dependencies: {missing_deps}")
                return False
            else:
                print("✓ Frontend dependencies check passed")
                return True
        else:
            print("✗ Frontend package.json not found")
            return False
            
    except Exception as e:
        print(f"✗ Frontend test error: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 50)
    print("CODING PLATFORM - END-TO-END TEST")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports()),
        ("Code Execution", test_code_execution()),
        ("Model Creation", test_models()),
        ("Frontend Setup", test_frontend_build())
    ]
    
    results = []
    for test_name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core tests passed! The coding platform is ready.")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)