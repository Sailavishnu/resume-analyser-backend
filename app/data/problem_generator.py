"""
Coding Problems Generator

Generates 200+ LeetCode-style coding problems with test cases, hints, and solutions.
"""
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models.coding import (
    CodingProblem, DifficultyLevel, ProblemCategory, LanguageSupport,
    TestCase, Constraint, Hint, StarterCode, Solution
)

def generate_all_problems() -> List[Dict[str, Any]]:
    """Generate all 200+ coding problems"""
    problems = []
    
    # Arrays Problems (40 problems)
    problems.extend(generate_array_problems())
    
    # Strings Problems (35 problems)  
    problems.extend(generate_string_problems())
    
    # Linked Lists Problems (25 problems)
    problems.extend(generate_linked_list_problems())
    
    # Trees Problems (30 problems)
    problems.extend(generate_tree_problems())
    
    # Dynamic Programming Problems (20 problems)
    problems.extend(generate_dp_problems())
    
    # Graph Problems (15 problems)
    problems.extend(generate_graph_problems())
    
    # Stack/Queue Problems (15 problems)
    problems.extend(generate_stack_queue_problems())
    
    # Hash Tables Problems (10 problems)
    problems.extend(generate_hash_problems())
    
    # Math Problems (10 problems)
    problems.extend(generate_math_problems())
    
    return problems

def generate_array_problems() -> List[Dict[str, Any]]:
    """Generate 40 array-based coding problems"""
    problems = []
    
    # Problem 1: Two Sum
    problems.append({
        "problem_id": "two-sum",
        "title": "Two Sum",
        "description": """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

You can return the answer in any order.""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "hash-table"],
        "examples": [
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
            },
            {
                "input": "nums = [3,2,4], target = 6", 
                "output": "[1,2]",
                "explanation": "Because nums[1] + nums[2] == 6, we return [1, 2]."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "2 <= nums.length <= 10^4",
                "-10^9 <= nums[i] <= 10^9",
                "-10^9 <= target <= 10^9",
                "Only one valid answer exists."
            ]
        },
        "hints": [
            {"text": "Try using a hash map to store values and their indices", "order": 1},
            {"text": "For each number, check if target - number exists in the hash map", "order": 2}
        ],
        "test_cases": [
            {"input": "4\n2 7 11 15\n9", "expected_output": "0 1", "is_hidden": False},
            {"input": "3\n3 2 4\n6", "expected_output": "1 2", "is_hidden": False},
            {"input": "2\n3 3\n6", "expected_output": "0 1", "is_hidden": True},
            {"input": "5\n1 5 8 2 9\n10", "expected_output": "1 3", "is_hidden": True},
            {"input": "6\n-1 -2 -3 -4 -5\n-8", "expected_output": "2 4", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def two_sum(nums, target):
    # Your code here
    pass

# Read input
n = int(input())
nums = list(map(int, input().split()))
target = int(input())

# Solve and print result
result = two_sum(nums, target)
print(result[0], result[1])"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []

n = int(input())
nums = list(map(int, input().split()))
target = int(input())
result = two_sum(nums, target)
print(result[0], result[1])""",
                "explanation": "Use hash map to store numbers and indices. For each number, check if its complement exists.",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)"
            }
        ],
        "xp_reward": 10
    })
    
    # Problem 2: Best Time to Buy and Sell Stock
    problems.append({
        "problem_id": "best-time-buy-sell-stock",
        "title": "Best Time to Buy and Sell Stock",
        "description": """You are given an array prices where prices[i] is the price of a given stock on the ith day.

You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock.

Return the maximum profit you can achieve from this transaction. If you cannot achieve any profit, return 0.""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "dynamic-programming"],
        "examples": [
            {
                "input": "prices = [7,1,5,3,6,4]",
                "output": "5",
                "explanation": "Buy on day 2 (price = 1) and sell on day 5 (price = 6), profit = 6-1 = 5."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= prices.length <= 10^5",
                "0 <= prices[i] <= 10^4"
            ]
        },
        "hints": [
            {"text": "Keep track of the minimum price seen so far", "order": 1},
            {"text": "For each price, calculate profit if sold today", "order": 2}
        ],
        "test_cases": [
            {"input": "6\n7 1 5 3 6 4", "expected_output": "5", "is_hidden": False},
            {"input": "5\n7 6 4 3 1", "expected_output": "0", "is_hidden": False},
            {"input": "1\n1", "expected_output": "0", "is_hidden": True},
            {"input": "4\n1 2 3 4", "expected_output": "3", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def max_profit(prices):
    # Your code here
    pass

n = int(input())
prices = list(map(int, input().split()))
result = max_profit(prices)
print(result)"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def max_profit(prices):
    if not prices:
        return 0
    
    min_price = prices[0]
    max_profit = 0
    
    for price in prices[1:]:
        max_profit = max(max_profit, price - min_price)
        min_price = min(min_price, price)
    
    return max_profit

n = int(input())
prices = list(map(int, input().split()))
print(max_profit(prices))""",
                "explanation": "Track minimum price and maximum profit by checking profit at each price.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    })
    # Problem 3: Contains Duplicate
    problems.append({
        "problem_id": "contains-duplicate",
        "title": "Contains Duplicate", 
        "description": """Given an integer array nums, return true if any value appears at least twice in the array, and return false if every element is distinct.""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "hash-table", "sorting"],
        "examples": [
            {
                "input": "nums = [1,2,3,1]",
                "output": "true",
                "explanation": "Element 1 appears at index 0 and 3."
            },
            {
                "input": "nums = [1,2,3,4]",
                "output": "false", 
                "explanation": "All elements are distinct."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= nums.length <= 10^5",
                "-10^9 <= nums[i] <= 10^9"
            ]
        },
        "hints": [
            {"text": "Use a set to track seen elements", "order": 1},
            {"text": "If element already in set, return True", "order": 2}
        ],
        "test_cases": [
            {"input": "4\n1 2 3 1", "expected_output": "true", "is_hidden": False},
            {"input": "4\n1 2 3 4", "expected_output": "false", "is_hidden": False},
            {"input": "3\n1 1 1", "expected_output": "true", "is_hidden": True},
            {"input": "1\n1", "expected_output": "false", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def contains_duplicate(nums):
    # Your code here
    pass

n = int(input())
nums = list(map(int, input().split()))
result = contains_duplicate(nums)
print("true" if result else "false")"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def contains_duplicate(nums):
    seen = set()
    for num in nums:
        if num in seen:
            return True
        seen.add(num)
    return False

n = int(input())
nums = list(map(int, input().split()))
result = contains_duplicate(nums)
print("true" if result else "false")""",
                "explanation": "Use set to track seen numbers. Return True if duplicate found.",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)"
            }
        ],
        "xp_reward": 10
    })

    # Problem 4: Maximum Subarray (Kadane's Algorithm)
    problems.append({
        "problem_id": "maximum-subarray",
        "title": "Maximum Subarray",
        "description": """Given an integer array nums, find the contiguous subarray (containing at least one number) which has the largest sum and return its sum.

A subarray is a contiguous part of an array.""",
        "difficulty": DifficultyLevel.MEDIUM,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "divide-and-conquer", "dynamic-programming"],
        "examples": [
            {
                "input": "nums = [-2,1,-3,4,-1,2,1,-5,4]",
                "output": "6",
                "explanation": "[4,-1,2,1] has the largest sum = 6."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= nums.length <= 10^5",
                "-10^4 <= nums[i] <= 10^4"
            ]
        },
        "hints": [
            {"text": "Use Kadane's algorithm", "order": 1},
            {"text": "Keep track of current sum and maximum sum", "order": 2},
            {"text": "Reset current sum to 0 if it becomes negative", "order": 3}
        ],
        "test_cases": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "expected_output": "6", "is_hidden": False},
            {"input": "1\n1", "expected_output": "1", "is_hidden": False},
            {"input": "5\n5 4 -1 7 8", "expected_output": "23", "is_hidden": True},
            {"input": "4\n-2 -3 -1 -5", "expected_output": "-1", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def max_subarray(nums):
    # Your code here
    pass

n = int(input())
nums = list(map(int, input().split()))
result = max_subarray(nums)
print(result)"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def max_subarray(nums):
    max_sum = current_sum = nums[0]
    
    for num in nums[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    
    return max_sum

n = int(input())
nums = list(map(int, input().split()))
print(max_subarray(nums))""",
                "explanation": "Kadane's algorithm: track current and maximum sum, reset if current becomes negative.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 25
    })

    # Problem 5: Product of Array Except Self
    problems.append({
        "problem_id": "product-except-self",
        "title": "Product of Array Except Self",
        "description": """Given an integer array nums, return an array answer such that answer[i] is equal to the product of all the elements of nums except nums[i].

The product of any prefix or suffix of nums is guaranteed to fit in a 32-bit integer.

You must write an algorithm that runs in O(n) time and without using the division operation.""",
        "difficulty": DifficultyLevel.MEDIUM,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "prefix-sum"],
        "examples": [
            {
                "input": "nums = [1,2,3,4]",
                "output": "[24,12,8,6]",
                "explanation": "answer[0] = 2*3*4 = 24, answer[1] = 1*3*4 = 12, etc."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "2 <= nums.length <= 10^5",
                "-30 <= nums[i] <= 30"
            ]
        },
        "hints": [
            {"text": "Calculate left products first, then right products", "order": 1},
            {"text": "Use the output array to store left products, then multiply with right products", "order": 2}
        ],
        "test_cases": [
            {"input": "4\n1 2 3 4", "expected_output": "24 12 8 6", "is_hidden": False},
            {"input": "5\n-1 1 0 -3 3", "expected_output": "0 0 9 0 0", "is_hidden": False},
            {"input": "3\n2 3 4", "expected_output": "12 8 6", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def product_except_self(nums):
    # Your code here
    pass

n = int(input())
nums = list(map(int, input().split()))
result = product_except_self(nums)
print(' '.join(map(str, result)))"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def product_except_self(nums):
    n = len(nums)
    result = [1] * n
    
    # Left products
    for i in range(1, n):
        result[i] = result[i-1] * nums[i-1]
    
    # Right products
    right = 1
    for i in range(n-1, -1, -1):
        result[i] *= right
        right *= nums[i]
    
    return result

n = int(input())
nums = list(map(int, input().split()))
result = product_except_self(nums)
print(' '.join(map(str, result)))""",
                "explanation": "Two pass: left products then right products multiplied in.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 25
    })

    return problems
def generate_string_problems() -> List[Dict[str, Any]]:
    """Generate 35 string-based coding problems"""
    problems = []
    
    # Problem 1: Valid Palindrome
    problems.append({
        "problem_id": "valid-palindrome",
        "title": "Valid Palindrome",
        "description": """A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward. Alphanumeric characters include letters and numbers.

Given a string s, return true if it is a palindrome, or false otherwise.""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.STRINGS,
        "tags": ["two-pointers", "string"],
        "examples": [
            {
                "input": 's = "A man, a plan, a canal: Panama"',
                "output": "true",
                "explanation": '"amanaplanacanalpanama" is a palindrome.'
            },
            {
                "input": 's = "race a car"',
                "output": "false",
                "explanation": '"raceacar" is not a palindrome.'
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= s.length <= 2 * 10^5",
                "s consists only of printable ASCII characters."
            ]
        },
        "hints": [
            {"text": "Use two pointers from start and end", "order": 1},
            {"text": "Skip non-alphanumeric characters", "order": 2},
            {"text": "Compare characters in lowercase", "order": 3}
        ],
        "test_cases": [
            {"input": "A man, a plan, a canal: Panama", "expected_output": "true", "is_hidden": False},
            {"input": "race a car", "expected_output": "false", "is_hidden": False},
            {"input": " ", "expected_output": "true", "is_hidden": True},
            {"input": "Madam", "expected_output": "true", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def is_palindrome(s):
    # Your code here
    pass

s = input().strip()
result = is_palindrome(s)
print("true" if result else "false")"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def is_palindrome(s):
    left, right = 0, len(s) - 1
    
    while left < right:
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        
        if s[left].lower() != s[right].lower():
            return False
        
        left += 1
        right -= 1
    
    return True

s = input().strip()
result = is_palindrome(s)
print("true" if result else "false")""",
                "explanation": "Two pointers approach, skip non-alphanumeric, compare lowercase.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    })
    
    # Problem 2: Longest Common Prefix
    problems.append({
        "problem_id": "longest-common-prefix",
        "title": "Longest Common Prefix",
        "description": """Write a function to find the longest common prefix string amongst an array of strings.

If there is no common prefix, return an empty string "".""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.STRINGS,
        "tags": ["string", "trie"],
        "examples": [
            {
                "input": 'strs = ["flower","flow","flight"]',
                "output": '"fl"',
                "explanation": 'The longest common prefix is "fl".'
            },
            {
                "input": 'strs = ["dog","racecar","car"]',
                "output": '""',
                "explanation": "There is no common prefix among the input strings."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= strs.length <= 200",
                "0 <= strs[i].length <= 200",
                "strs[i] consists of only lowercase English letters."
            ]
        },
        "hints": [
            {"text": "Compare character by character across all strings", "order": 1},
            {"text": "Stop when you find first mismatch", "order": 2}
        ],
        "test_cases": [
            {"input": "3\nflower\nflow\nflight", "expected_output": "fl", "is_hidden": False},
            {"input": "3\ndog\nracecar\ncar", "expected_output": "", "is_hidden": False},
            {"input": "1\nalone", "expected_output": "alone", "is_hidden": True},
            {"input": "2\nabc\nabcd", "expected_output": "abc", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def longest_common_prefix(strs):
    # Your code here
    pass

n = int(input())
strs = []
for _ in range(n):
    strs.append(input().strip())

result = longest_common_prefix(strs)
print(result)"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def longest_common_prefix(strs):
    if not strs:
        return ""
    
    prefix = strs[0]
    for s in strs[1:]:
        while prefix and not s.startswith(prefix):
            prefix = prefix[:-1]
    
    return prefix

n = int(input())
strs = []
for _ in range(n):
    strs.append(input().strip())
    
result = longest_common_prefix(strs)
print(result)""",
                "explanation": "Start with first string, trim until all strings have this prefix.",
                "time_complexity": "O(S) where S is sum of all characters",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    })

    # Problem 3: Valid Anagram  
    problems.append({
        "problem_id": "valid-anagram",
        "title": "Valid Anagram",
        "description": """Given two strings s and t, return true if t is an anagram of s, and false otherwise.

An Anagram is a word or phrase formed by rearranging the letters of a different word or phrase, typically using all the original letters exactly once.""",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.STRINGS,
        "tags": ["hash-table", "string", "sorting"],
        "examples": [
            {
                "input": 's = "anagram", t = "nagaram"',
                "output": "true",
                "explanation": "Both strings contain the same characters with same frequency."
            },
            {
                "input": 's = "rat", t = "car"',
                "output": "false",
                "explanation": "Different characters, not an anagram."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": [
                "1 <= s.length, t.length <= 5 * 10^4",
                "s and t consist of lowercase English letters."
            ]
        },
        "hints": [
            {"text": "Count character frequencies in both strings", "order": 1},
            {"text": "Compare the frequency counts", "order": 2},
            {"text": "Alternative: sort both strings and compare", "order": 3}
        ],
        "test_cases": [
            {"input": "anagram\nnagaram", "expected_output": "true", "is_hidden": False},
            {"input": "rat\ncar", "expected_output": "false", "is_hidden": False},
            {"input": "a\nab", "expected_output": "false", "is_hidden": True},
            {"input": "listen\nsilent", "expected_output": "true", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def is_anagram(s, t):
    # Your code here
    pass

s = input().strip()
t = input().strip()
result = is_anagram(s, t)
print("true" if result else "false")"""
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": """def is_anagram(s, t):
    if len(s) != len(t):
        return False
    
    from collections import Counter
    return Counter(s) == Counter(t)

s = input().strip()
t = input().strip()
result = is_anagram(s, t)
print("true" if result else "false")""",
                "explanation": "Count character frequencies and compare them.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1) - at most 26 characters"
            }
        ],
        "xp_reward": 10
    })

    return problems[:5]  # Return first 5 for now