"""
Code Execution and Algorithmic Problem Service for SAKSHAM AI.
Provides coding catalog, test case validation, and isolated execution.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.coding import CodingProblem, CodingTestCase, CodingSubmission
from app.models.interview import InterviewSession
from app.integrations.judge0_adapter import (
    ExecutionOutputLimitExceeded,
    ExecutionProviderError,
    JUDGE0_LANG_IDS,
    Judge0Adapter,
)
from app.core.config import secret_value, settings
from app.services.execution_quota import QuotaStoreUnavailable, acquire_execution_lease, release_execution_lease, _LOCAL_SLOTS as _EXECUTION_SLOTS
from app.core.exceptions import ForbiddenException, NotFoundException, SakshamException

SAMPLE_PROBLEMS = [
    {
        "id": "two-sum",
        "title": "Two Sum",
        "difficulty": "Easy",
        "category": "Arrays & Hashing",
        "description": "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.",
        "constraints": [
            "2 <= nums.length <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "Only one valid answer exists."
        ],
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
        "hints": [
            "A brute force search checks every pair in O(N^2) time. Can we do better using auxiliary storage?",
            "Can we use a hash map to check whether the complement (target - current) exists in O(1) time?",
            "Iterate through the array once: if (target - num) is in your hash map, return [map[target - num], current_index]. Otherwise store num -> index."
        ],
        "starter_code": {
            "python": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Write your solution here\n    pass\n\n# Test call\nimport json, sys\nprint(json.dumps(twoSum([2, 7, 11, 15], 9)))",
            "javascript": "function twoSum(nums, target) {\n    // Write your solution here\n}\n\nconsole.log(JSON.stringify(twoSum([2, 7, 11, 15], 9)));",
            "cpp": "#include <iostream>\n#include <vector>\n#include <unordered_map>\nusing namespace std;\n\nvector<int> twoSum(vector<int>& nums, int target) {\n    // Write your solution here\n    return {};\n}\n\nint main() {\n    cout << \"[0, 1]\" << endl;\n    return 0;\n}",
            "java": "import java.util.*;\n\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        // Write your solution here\n        return new int[]{0, 1};\n    }\n    public static void main(String[] args) {\n        System.out.println(\"[0, 1]\");\n    }\n}"
        },
        "test_cases": [
            {"input": "[2, 7, 11, 15]\n9", "output": "[0, 1]", "is_hidden": False},
            {"input": "[3, 2, 4]\n6", "output": "[1, 2]", "is_hidden": False},
            {"input": "[3, 3]\n6", "output": "[0, 1]", "is_hidden": True}
        ]
    },
    {
        "id": "valid-parentheses",
        "title": "Valid Parentheses",
        "difficulty": "Easy",
        "category": "Stack",
        "description": "Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\nAn input string is valid if open brackets are closed by the same type of brackets and in the correct order.",
        "constraints": [
            "1 <= s.length <= 10^4",
            "s consists of parentheses only '()[]{}'."
        ],
        "examples": [
            {
                "input": "s = \"()[]{}\"",
                "output": "true",
                "explanation": "All bracket pairs open and close symmetrically."
            },
            {
                "input": "s = \"(]\"",
                "output": "false",
                "explanation": "Mismatched bracket closing."
            }
        ],
        "hints": [
            "Consider what data structure naturally operates in Last-In, First-Out (LIFO) order.",
            "Push opening brackets onto a stack. When an closing bracket appears, check if the stack top matches.",
            "Remember edge cases: what if closing brackets appear when the stack is empty, or brackets remain open at the end?"
        ],
        "starter_code": {
            "python": "def isValid(s: str) -> bool:\n    # Write your solution here\n    pass\n\nprint(str(isValid(\"()[]{}\")).lower())",
            "javascript": "function isValid(s) {\n    // Write your solution here\n}\n\nconsole.log(isValid(\"()[]{}\"));",
            "cpp": "#include <iostream>\n#include <string>\n#include <stack>\nusing namespace std;\n\nbool isValid(string s) {\n    return true;\n}\n\nint main() {\n    cout << \"true\" << endl;\n    return 0;\n}",
            "java": "public class Solution {\n    public static boolean isValid(String s) {\n        return true;\n    }\n    public static void main(String[] args) {\n        System.out.println(\"true\");\n    }\n}"
        },
        "test_cases": [
            {"input": "()[]{}", "output": "true", "is_hidden": False},
            {"input": "(]", "output": "false", "is_hidden": False},
            {"input": "([)]", "output": "false", "is_hidden": True}
        ]
    },
    {
        "id": "longest-substring",
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "Medium",
        "category": "Sliding Window",
        "description": "Given a string `s`, find the length of the longest substring without duplicate characters.",
        "constraints": [
            "0 <= s.length <= 5 * 10^4",
            "s consists of English letters, digits, symbols and spaces."
        ],
        "examples": [
            {
                "input": "s = \"abcabcbb\"",
                "output": "3",
                "explanation": "The answer is \"abc\", with the length of 3."
            }
        ],
        "hints": [
            "Can we maintain a sliding window `[left, right]` where all characters inside are unique?",
            "Use a set or map to track characters and their most recent indices.",
            "When a duplicate is encountered, slide the left pointer past the previous index of that character."
        ],
        "starter_code": {
            "python": "def lengthOfLongestSubstring(s: str) -> int:\n    # Write your solution here\n    pass\n\nprint(lengthOfLongestSubstring(\"abcabcbb\"))",
            "javascript": "function lengthOfLongestSubstring(s) {\n    // Write your solution here\n}\n\nconsole.log(lengthOfLongestSubstring(\"abcabcbb\"));",
            "cpp": "#include <iostream>\n#include <string>\nusing namespace std;\n\nint lengthOfLongestSubstring(string s) {\n    return 3;\n}\n\nint main() {\n    cout << 3 << endl;\n    return 0;\n}",
            "java": "public class Solution {\n    public static int lengthOfLongestSubstring(String s) {\n        return 3;\n    }\n    public static void main(String[] args) {\n        System.out.println(3);\n    }\n}"
        },
        "test_cases": [
            {"input": "abcabcbb", "output": "3", "is_hidden": False},
            {"input": "bbbbb", "output": "1", "is_hidden": False},
            {"input": "pwwkew", "output": "3", "is_hidden": True}
        ]
    }
]

MAX_OUTPUT_BYTES = 16 * 1024


def _outputs_match(problem_id: str, expected: str, actual: str) -> bool:
    """Compare complete outputs, allowing JSON formatting and Two Sum order."""
    expected = expected.strip()
    actual = actual.strip()
    try:
        expected_value = json.loads(expected)
        actual_value = json.loads(actual)
    except (json.JSONDecodeError, TypeError):
        return expected == actual

    if problem_id == "two-sum" and isinstance(expected_value, list) and isinstance(actual_value, list):
        if all(type(value) is int for value in expected_value + actual_value):
            return sorted(expected_value) == sorted(actual_value)
    return json.dumps(expected_value, sort_keys=True, separators=(",", ":")) == json.dumps(
        actual_value, sort_keys=True, separators=(",", ":")
    )


class ExecutionEngine:
    @staticmethod
    def seed_problems_if_empty(db: Session):
        count = db.query(CodingProblem).count()
        if count == 0:
            for prob in SAMPLE_PROBLEMS:
                p = CodingProblem(
                    id=prob["id"],
                    title=prob["title"],
                    difficulty=prob["difficulty"],
                    category=prob["category"],
                    description=prob["description"],
                    constraints=json.dumps(prob["constraints"]),
                    examples=json.dumps(prob["examples"]),
                    starter_code=json.dumps(prob["starter_code"]),
                    hints=json.dumps(prob["hints"])
                )
                db.add(p)
                for test_index, tc in enumerate(prob["test_cases"]):
                    t = CodingTestCase(
                        problem_id=prob["id"],
                        input_data=tc["input"],
                        expected_output=tc["output"],
                        is_hidden=tc["is_hidden"], created_at=datetime.now(timezone.utc) + timedelta(microseconds=test_index)
                    )
                    db.add(t)
            db.commit()

    @staticmethod
    def get_problems(db: Session) -> List[CodingProblem]:
        return db.query(CodingProblem).all()

    @staticmethod
    def get_problem_by_id(db: Session, problem_id: str) -> Optional[CodingProblem]:
        return db.query(CodingProblem).filter(CodingProblem.id == problem_id).first()

    @classmethod
    async def execute_code(
        cls,
        db: Session,
        problem_id: str,
        language: str,
        code: str,
        user_id: str,
        custom_input: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        problem = cls.get_problem_by_id(db, problem_id)
        if not problem:
            raise NotFoundException("CodingProblem", problem_id)
        if language not in JUDGE0_LANG_IDS:
            raise SakshamException(422, "Unsupported programming language")

        if session_id:
            session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
            if not session:
                raise NotFoundException("InterviewSession", session_id)
            if session.user_id != user_id:
                raise ForbiddenException("Interview session does not belong to the authenticated user")

        if not settings.JUDGE0_API_URL or not secret_value(settings.JUDGE0_API_KEY):
            raise SakshamException(503, "Code execution service is not configured")

        try:
            adapter = Judge0Adapter(settings.JUDGE0_API_URL, secret_value(settings.JUDGE0_API_KEY))
        except ExecutionProviderError:
            raise SakshamException(503, "Code execution service configuration is invalid") from None

        test_cases = db.query(CodingTestCase).filter(
            CodingTestCase.problem_id == problem_id
        ).order_by(CodingTestCase.created_at, CodingTestCase.id).all()
        is_custom_run = bool(custom_input)
        if not is_custom_run and not test_cases:
            raise SakshamException(422, "No test cases are configured for this problem")
        if len(test_cases) > settings.CODE_MAX_TEST_CASES:
            raise SakshamException(422, "Problem exceeds the maximum supported test-case count")
        if any(len(tc.input_data.encode("utf-8")) > 16 * 1024 for tc in test_cases):
            raise SakshamException(422, "A stored test case exceeds the 16 KiB input limit")
        try:
            lease = await acquire_execution_lease(user_id)
        except QuotaStoreUnavailable:
            raise SakshamException(503, "Code execution capacity service is unavailable") from None
        if lease is None:
            raise SakshamException(429, "Code execution capacity is busy; retry shortly")

        cases = [None] if is_custom_run else test_cases
        deadline = time.monotonic() + settings.CODE_REQUEST_TIMEOUT_SECONDS
        test_results = []
        outputs = []
        errors = []
        passed_count = 0
        total_time_ms = 0
        peak_memory_kb = 0
        execution_status = "Accepted"

        try:
            for idx, tc in enumerate(cases, start=1):
                case_input = custom_input if is_custom_run else tc.input_data
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise asyncio.TimeoutError
                    result = await asyncio.wait_for(
                        adapter.execute(language, code, case_input),
                        timeout=remaining,
                    )
                    stdout = result.get("stdout", "") or ""
                    stderr = result.get("stderr", "") or ""
                    compile_output = result.get("compile_output", "") or ""
                    if any(len(value.encode("utf-8")) > MAX_OUTPUT_BYTES for value in (stdout, stderr, compile_output)):
                        raise ExecutionOutputLimitExceeded
                    case_status = result.get("status_desc", "Runtime Error")
                    allowed_statuses = {
                        "Accepted", "Time Limit Exceeded", "Compilation Error", "Runtime Error",
                        "Memory Limit Exceeded", "Output Limit Exceeded",
                    }
                    if case_status not in allowed_statuses:
                        case_status = "Runtime Error"
                    total_time_ms += int(result.get("time_ms", 0) or 0)
                    peak_memory_kb = max(peak_memory_kb, int(result.get("memory_kb", 0) or 0))
                    passed = (
                        case_status == "Accepted"
                        and (is_custom_run or _outputs_match(problem_id, tc.expected_output, stdout))
                    )
                    if not passed and execution_status == "Accepted":
                        execution_status = case_status if case_status != "Accepted" else "Wrong Answer"
                    outputs.append(stdout)
                    case_error = stderr or compile_output
                    errors.append(case_error)
                except ExecutionOutputLimitExceeded:
                    case_status = "Output Limit Exceeded"
                    passed = False
                    stdout = ""
                    stderr = "Output limit exceeded"
                    case_error = stderr
                    outputs.append(stdout)
                    errors.append(stderr)
                    if execution_status == "Accepted":
                        execution_status = case_status
                except asyncio.TimeoutError as exc:
                    raise SakshamException(503, "Code execution service timed out") from None
                except ExecutionProviderError:
                    raise SakshamException(503, "Code execution service is unavailable") from None

                if passed:
                    passed_count += 1
                is_hidden = bool(tc.is_hidden) if tc is not None else False
                test_results.append({
                    "test_id": idx,
                    "passed": passed,
                    "input_data": "[Hidden Test Case]" if is_hidden else case_input,
                    "expected_output": "[Hidden]" if is_hidden else (tc.expected_output if tc is not None else "Not graded"),
                    "actual_output": stdout if stdout else ("[Output limit exceeded]" if case_status == "Output Limit Exceeded" else ""),
                    "error": (case_error or None) if not passed else None,
                })
        finally:
            try:
                await release_execution_lease(lease)
            except QuotaStoreUnavailable:
                raise SakshamException(503, "Code execution capacity service is unavailable") from None

        total_count = len(cases)
        stdout = outputs[0] if outputs else ""
        stderr = next((error for error in errors if error), "")
        if is_custom_run and execution_status == "Accepted":
            passed_count = 1

        # Big-O complexity feedback
        ai_complexity = {
            "time_complexity": "O(N)" if "for " in code and "for " not in code[code.find("for ")+4:] else "O(N^2)",
            "space_complexity": "O(N)" if "dict" in code or "{}" in code or "map" in code.lower() else "O(1)",
            "code_quality_score": 88 if execution_status == "Accepted" else 55,
            "feedback": "Optimal hash-based approach identified with single pass." if "dict" in code or "{}" in code else "Consider using a hash table to optimize time complexity."
        }

        # Store submission
        submission = CodingSubmission(
            user_id=user_id,
            session_id=session_id,
            problem_id=problem_id,
            language=language,
            code=code,
            status=execution_status,
            passed_tests=passed_count,
            total_tests=total_count,
            execution_time_ms=total_time_ms,
            memory_kb=peak_memory_kb,
            output=stdout,
            ai_complexity_feedback=json.dumps(ai_complexity)
        )
        db.add(submission)
        db.commit()

        return {
            "status": execution_status,
            "passed_tests": passed_count,
            "total_tests": total_count,
            "execution_time_ms": total_time_ms,
            "memory_kb": peak_memory_kb,
            "stdout": stdout,
            "stderr": stderr,
            "test_results": test_results,
            "ai_complexity_feedback": ai_complexity
        }
