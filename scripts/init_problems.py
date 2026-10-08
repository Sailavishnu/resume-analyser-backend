#!/usr/bin/env python3
"""
Initialize coding problems - one per category for testing
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.coding import DifficultyLevel, ProblemCategory, LanguageSupport
from app.cloud.coding_collections import CODING_PROBLEMS_COLLECTION

async def init_minimal_problems():
    """Initialize one problem per category"""
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ppp_db
    collection = db[CODING_PROBLEMS_COLLECTION]
    
    # Array Problem - Two Sum
    array_problem = {
        "problem_id": "two-sum",
        "title": "Two Sum", 
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.ARRAYS,
        "tags": ["array", "hash-table"],
        "examples": [
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"]
        },
        "hints": [
            {"text": "Use a hash map to store values and their indices", "order": 1}
        ],
        "test_cases": [
            {"input": "4\n2 7 11 15\n9", "expected_output": "0 1", "is_hidden": False},
            {"input": "3\n3 2 4\n6", "expected_output": "1 2", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def two_sum(nums, target):\n    pass\n\nn = int(input())\nnums = list(map(int, input().split()))\ntarget = int(input())\nresult = two_sum(nums, target)\nprint(result[0], result[1])"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def two_sum(nums, target):\n    num_map = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in num_map:\n            return [num_map[complement], i]\n        num_map[num] = i\n    return []\n\nn = int(input())\nnums = list(map(int, input().split()))\ntarget = int(input())\nresult = two_sum(nums, target)\nprint(result[0], result[1])",
                "explanation": "Use hash map to find complement",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)"
            }
        ],
        "xp_reward": 10
    }
    
    # String Problem - Valid Palindrome
    string_problem = {
        "problem_id": "valid-palindrome",
        "title": "Valid Palindrome",
        "description": "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.STRINGS,
        "tags": ["two-pointers", "string"],
        "examples": [
            {
                "input": 's = "A man, a plan, a canal: Panama"',
                "output": "true",
                "explanation": '"amanaplanacanalpanama" is a palindrome.'
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["1 <= s.length <= 2 * 10^5"]
        },
        "hints": [
            {"text": "Use two pointers from start and end", "order": 1}
        ],
        "test_cases": [
            {"input": "A man, a plan, a canal: Panama", "expected_output": "true", "is_hidden": False},
            {"input": "race a car", "expected_output": "false", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_palindrome(s):\n    pass\n\ns = input().strip()\nresult = is_palindrome(s)\nprint('true' if result else 'false')"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_palindrome(s):\n    left, right = 0, len(s) - 1\n    while left < right:\n        while left < right and not s[left].isalnum():\n            left += 1\n        while left < right and not s[right].isalnum():\n            right -= 1\n        if s[left].lower() != s[right].lower():\n            return False\n        left += 1\n        right -= 1\n    return True\n\ns = input().strip()\nresult = is_palindrome(s)\nprint('true' if result else 'false')",
                "explanation": "Two pointers, skip non-alphanumeric",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    }
    
    # Linked List Problem - Reverse Linked List
    linkedlist_problem = {
        "problem_id": "reverse-linked-list",
        "title": "Reverse Linked List",
        "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.LINKED_LISTS,
        "tags": ["linked-list", "recursion"],
        "examples": [
            {
                "input": "head = [1,2,3,4,5]",
                "output": "[5,4,3,2,1]",
                "explanation": "Reverse the linked list."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["0 <= The number of nodes <= 5000", "-5000 <= Node.val <= 5000"]
        },
        "hints": [
            {"text": "Use three pointers: prev, curr, next", "order": 1}
        ],
        "test_cases": [
            {"input": "5\n1 2 3 4 5", "expected_output": "5 4 3 2 1", "is_hidden": False},
            {"input": "2\n1 2", "expected_output": "2 1", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverse_list(head):\n    pass\n\n# Read and build list\nn = int(input())\nif n == 0:\n    print()\nelse:\n    values = list(map(int, input().split()))\n    head = ListNode(values[0])\n    curr = head\n    for val in values[1:]:\n        curr.next = ListNode(val)\n        curr = curr.next\n    \n    result = reverse_list(head)\n    output = []\n    while result:\n        output.append(str(result.val))\n        result = result.next\n    print(' '.join(output))"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        next_temp = curr.next\n        curr.next = prev\n        prev = curr\n        curr = next_temp\n    return prev\n\nn = int(input())\nif n == 0:\n    print()\nelse:\n    values = list(map(int, input().split()))\n    head = ListNode(values[0])\n    curr = head\n    for val in values[1:]:\n        curr.next = ListNode(val)\n        curr = curr.next\n    \n    result = reverse_list(head)\n    output = []\n    while result:\n        output.append(str(result.val))\n        result = result.next\n    print(' '.join(output))",
                "explanation": "Use three pointers to reverse links",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    }
    
    # Tree Problem - Maximum Depth of Binary Tree
    tree_problem = {
        "problem_id": "maximum-depth-binary-tree",
        "title": "Maximum Depth of Binary Tree",
        "description": "Given the root of a binary tree, return its maximum depth. A binary tree's maximum depth is the number of nodes along the longest path from the root node down to the farthest leaf node.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.TREES,
        "tags": ["tree", "depth-first-search", "breadth-first-search", "binary-tree"],
        "examples": [
            {
                "input": "root = [3,9,20,null,null,15,7]",
                "output": "3",
                "explanation": "The maximum depth is 3."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["0 <= The number of nodes <= 10^4", "-100 <= Node.val <= 100"]
        },
        "hints": [
            {"text": "Use recursion to find max depth of left and right subtrees", "order": 1}
        ],
        "test_cases": [
            {"input": "7\n3 9 20 -1 -1 15 7", "expected_output": "3", "is_hidden": False},
            {"input": "2\n1 -1 2", "expected_output": "2", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef max_depth(root):\n    pass\n\n# Build tree from level order\nfrom collections import deque\nn = int(input())\nif n == 0:\n    print(0)\nelse:\n    values = input().split()\n    root = TreeNode(int(values[0]))\n    queue = deque([root])\n    i = 1\n    while queue and i < len(values):\n        node = queue.popleft()\n        if i < len(values) and values[i] != '-1':\n            node.left = TreeNode(int(values[i]))\n            queue.append(node.left)\n        i += 1\n        if i < len(values) and values[i] != '-1':\n            node.right = TreeNode(int(values[i]))\n            queue.append(node.right)\n        i += 1\n    \n    result = max_depth(root)\n    print(result)"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef max_depth(root):\n    if not root:\n        return 0\n    return 1 + max(max_depth(root.left), max_depth(root.right))\n\nfrom collections import deque\nn = int(input())\nif n == 0:\n    print(0)\nelse:\n    values = input().split()\n    root = TreeNode(int(values[0]))\n    queue = deque([root])\n    i = 1\n    while queue and i < len(values):\n        node = queue.popleft()\n        if i < len(values) and values[i] != '-1':\n            node.left = TreeNode(int(values[i]))\n            queue.append(node.left)\n        i += 1\n        if i < len(values) and values[i] != '-1':\n            node.right = TreeNode(int(values[i]))\n            queue.append(node.right)\n        i += 1\n    \n    result = max_depth(root)\n    print(result)",
                "explanation": "Recursively find max of left and right depths + 1",
                "time_complexity": "O(n)",
                "space_complexity": "O(h) where h is height"
            }
        ],
        "xp_reward": 10
    }
    
    # DP Problem - Climbing Stairs
    dp_problem = {
        "problem_id": "climbing-stairs",
        "title": "Climbing Stairs",
        "description": "You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.DYNAMIC_PROGRAMMING,
        "tags": ["math", "dynamic-programming", "memoization"],
        "examples": [
            {
                "input": "n = 2",
                "output": "2",
                "explanation": "There are two ways to climb to the top: 1+1 steps or 2 steps."
            },
            {
                "input": "n = 3", 
                "output": "3",
                "explanation": "Three ways: 1+1+1, 1+2, or 2+1."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["1 <= n <= 45"]
        },
        "hints": [
            {"text": "This is a Fibonacci sequence problem", "order": 1},
            {"text": "dp[i] = dp[i-1] + dp[i-2]", "order": 2}
        ],
        "test_cases": [
            {"input": "2", "expected_output": "2", "is_hidden": False},
            {"input": "3", "expected_output": "3", "is_hidden": False},
            {"input": "4", "expected_output": "5", "is_hidden": True},
            {"input": "5", "expected_output": "8", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def climb_stairs(n):\n    pass\n\nn = int(input())\nresult = climb_stairs(n)\nprint(result)"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def climb_stairs(n):\n    if n <= 1:\n        return 1\n    \n    dp = [0] * (n + 1)\n    dp[0] = dp[1] = 1\n    \n    for i in range(2, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    \n    return dp[n]\n\nn = int(input())\nresult = climb_stairs(n)\nprint(result)",
                "explanation": "Dynamic programming: ways to reach step i = ways to reach i-1 + ways to reach i-2",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)"
            }
        ],
        "xp_reward": 10
    }
    
    # Graph Problem - Number of Islands
    graph_problem = {
        "problem_id": "number-of-islands",
        "title": "Number of Islands", 
        "description": "Given an m x n 2D binary grid which represents a map of '1's (land) and '0's (water), return the number of islands. An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically.",
        "difficulty": DifficultyLevel.MEDIUM,
        "category": ProblemCategory.GRAPHS,
        "tags": ["array", "depth-first-search", "breadth-first-search", "union-find", "matrix"],
        "examples": [
            {
                "input": 'grid = [["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]',
                "output": "1",
                "explanation": "There is 1 island."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["m == grid.length", "n == grid[i].length", "1 <= m, n <= 300"]
        },
        "hints": [
            {"text": "Use DFS or BFS to explore connected components", "order": 1},
            {"text": "Mark visited cells to avoid revisiting", "order": 2}
        ],
        "test_cases": [
            {"input": "4 5\n11110\n11010\n11000\n00000", "expected_output": "1", "is_hidden": False},
            {"input": "4 5\n11000\n11000\n00100\n00011", "expected_output": "3", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def num_islands(grid):\n    pass\n\nm, n = map(int, input().split())\ngrid = []\nfor _ in range(m):\n    row = list(input().strip())\n    grid.append(row)\n\nresult = num_islands(grid)\nprint(result)"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def num_islands(grid):\n    if not grid:\n        return 0\n    \n    def dfs(i, j):\n        if i < 0 or i >= len(grid) or j < 0 or j >= len(grid[0]) or grid[i][j] != '1':\n            return\n        grid[i][j] = '0'  # Mark as visited\n        dfs(i+1, j)\n        dfs(i-1, j)\n        dfs(i, j+1)\n        dfs(i, j-1)\n    \n    count = 0\n    for i in range(len(grid)):\n        for j in range(len(grid[0])):\n            if grid[i][j] == '1':\n                count += 1\n                dfs(i, j)\n    \n    return count\n\nm, n = map(int, input().split())\ngrid = []\nfor _ in range(m):\n    row = list(input().strip())\n    grid.append(row)\n\nresult = num_islands(grid)\nprint(result)",
                "explanation": "DFS to explore connected land cells, count islands",
                "time_complexity": "O(m*n)",
                "space_complexity": "O(m*n) for recursion stack"
            }
        ],
        "xp_reward": 25
    }
    
    # Stack Problem - Valid Parentheses
    stack_problem = {
        "problem_id": "valid-parentheses",
        "title": "Valid Parentheses",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if: Open brackets must be closed by the same type of brackets. Open brackets must be closed in the correct order.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.STACK_QUEUE,
        "tags": ["string", "stack"],
        "examples": [
            {
                "input": 's = "()"',
                "output": "true",
                "explanation": "Valid parentheses."
            },
            {
                "input": 's = "()[]{}"',
                "output": "true",
                "explanation": "All brackets are properly closed."
            },
            {
                "input": 's = "(]"',
                "output": "false",
                "explanation": "Mismatched brackets."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["1 <= s.length <= 10^4", "s consists of parentheses only '()[]{}'"]
        },
        "hints": [
            {"text": "Use a stack to keep track of opening brackets", "order": 1},
            {"text": "When you see closing bracket, check if it matches top of stack", "order": 2}
        ],
        "test_cases": [
            {"input": "()", "expected_output": "true", "is_hidden": False},
            {"input": "()[]{}", "expected_output": "true", "is_hidden": False},
            {"input": "(]", "expected_output": "false", "is_hidden": False},
            {"input": "([)]", "expected_output": "false", "is_hidden": True},
            {"input": "{[]}", "expected_output": "true", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_valid(s):\n    pass\n\ns = input().strip()\nresult = is_valid(s)\nprint('true' if result else 'false')"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_valid(s):\n    stack = []\n    mapping = {')': '(', '}': '{', ']': '['}\n    \n    for char in s:\n        if char in mapping:\n            if not stack or stack.pop() != mapping[char]:\n                return False\n        else:\n            stack.append(char)\n    \n    return not stack\n\ns = input().strip()\nresult = is_valid(s)\nprint('true' if result else 'false')",
                "explanation": "Use stack to match opening and closing brackets",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)"
            }
        ],
        "xp_reward": 10
    }
    
    # Hash Table Problem - Two Sum (variant)
    hash_problem = {
        "problem_id": "group-anagrams",
        "title": "Group Anagrams",
        "description": "Given an array of strings strs, group the anagrams together. You can return the answer in any order. An Anagram is a word or phrase formed by rearranging the letters of a different word or phrase, typically using all the original letters exactly once.",
        "difficulty": DifficultyLevel.MEDIUM,
        "category": ProblemCategory.HASH_TABLES,
        "tags": ["array", "hash-table", "string", "sorting"],
        "examples": [
            {
                "input": 'strs = ["eat","tea","tan","ate","nat","bat"]',
                "output": '[["bat"],["nat","tan"],["ate","eat","tea"]]',
                "explanation": "Group words that are anagrams of each other."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["1 <= strs.length <= 10^4", "0 <= strs[i].length <= 100"]
        },
        "hints": [
            {"text": "Use sorted string as key to group anagrams", "order": 1},
            {"text": "Hash table with sorted string as key", "order": 2}
        ],
        "test_cases": [
            {"input": "6\neat\ntea\ntan\nate\nnat\nbat", "expected_output": "bat\nnat tan\nate eat tea", "is_hidden": False},
            {"input": "1\na", "expected_output": "a", "is_hidden": False}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def group_anagrams(strs):\n    pass\n\nn = int(input())\nstrs = []\nfor _ in range(n):\n    strs.append(input().strip())\n\nresult = group_anagrams(strs)\nfor group in result:\n    print(' '.join(sorted(group)))"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def group_anagrams(strs):\n    from collections import defaultdict\n    groups = defaultdict(list)\n    \n    for s in strs:\n        key = ''.join(sorted(s))\n        groups[key].append(s)\n    \n    return list(groups.values())\n\nn = int(input())\nstrs = []\nfor _ in range(n):\n    strs.append(input().strip())\n\nresult = group_anagrams(strs)\nfor group in result:\n    print(' '.join(sorted(group)))",
                "explanation": "Use sorted string as hash key to group anagrams",
                "time_complexity": "O(n * m log m) where m is avg string length",
                "space_complexity": "O(n * m)"
            }
        ],
        "xp_reward": 25
    }
    
    # Math Problem - Palindrome Number
    math_problem = {
        "problem_id": "palindrome-number",
        "title": "Palindrome Number",
        "description": "Given an integer x, return true if x is palindrome integer. An integer is a palindrome when it reads the same backward as forward.",
        "difficulty": DifficultyLevel.EASY,
        "category": ProblemCategory.MATH,
        "tags": ["math"],
        "examples": [
            {
                "input": "x = 121",
                "output": "true",
                "explanation": "121 reads as 121 from left to right and from right to left."
            },
            {
                "input": "x = -121",
                "output": "false",
                "explanation": "From left to right, it reads -121. From right to left, it becomes 121-."
            }
        ],
        "constraints": {
            "time_limit": 2000,
            "memory_limit": 256,
            "input_constraints": ["-2^31 <= x <= 2^31 - 1"]
        },
        "hints": [
            {"text": "Negative numbers are not palindromes", "order": 1},
            {"text": "Reverse the number and compare with original", "order": 2}
        ],
        "test_cases": [
            {"input": "121", "expected_output": "true", "is_hidden": False},
            {"input": "-121", "expected_output": "false", "is_hidden": False},
            {"input": "10", "expected_output": "false", "is_hidden": True},
            {"input": "1221", "expected_output": "true", "is_hidden": True}
        ],
        "starter_codes": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_palindrome(x):\n    pass\n\nx = int(input())\nresult = is_palindrome(x)\nprint('true' if result else 'false')"
            }
        ],
        "solutions": [
            {
                "language": LanguageSupport.PYTHON,
                "code": "def is_palindrome(x):\n    if x < 0:\n        return False\n    \n    original = x\n    reversed_num = 0\n    \n    while x > 0:\n        reversed_num = reversed_num * 10 + x % 10\n        x //= 10\n    \n    return original == reversed_num\n\nx = int(input())\nresult = is_palindrome(x)\nprint('true' if result else 'false')",
                "explanation": "Reverse the number mathematically and compare with original",
                "time_complexity": "O(log n)",
                "space_complexity": "O(1)"
            }
        ],
        "xp_reward": 10
    }
    
    # Insert all problems
    problems = [
        array_problem, string_problem, linkedlist_problem, tree_problem,
        dp_problem, graph_problem, stack_problem, hash_problem, math_problem
    ]
    
    print("Inserting problems...")
    for problem in problems:
        try:
            await collection.insert_one(problem)
            print(f"✓ Created: {problem['title']}")
        except Exception as e:
            print(f"✗ Failed to create {problem['title']}: {e}")
    
    print(f"\nCompleted! Inserted {len(problems)} problems.")
    client.close()

if __name__ == "__main__":
    asyncio.run(init_minimal_problems())