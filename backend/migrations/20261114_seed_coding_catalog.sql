-- Seed the built-in coding catalog for fresh production databases.

-- This migration is additive: existing problem rows and test cases are preserved.

BEGIN;

INSERT INTO coding_problems (id, title, difficulty, category, description, constraints, examples, starter_code, hints)
VALUES ('two-sum',
    'Two Sum',
    'Easy',
    'Arrays & Hashing',
    'Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.

You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.',
    '["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9", "-10^9 <= target <= 10^9", "Only one valid answer exists."]',
    '[{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."}, {"input": "nums = [3,2,4], target = 6", "output": "[1,2]", "explanation": "Because nums[1] + nums[2] == 6, we return [1, 2]."}]',
    '{"python": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Write your solution here\n    pass\n\n# Test call\nimport json, sys\nprint(json.dumps(twoSum([2, 7, 11, 15], 9)))", "javascript": "function twoSum(nums, target) {\n    // Write your solution here\n}\n\nconsole.log(JSON.stringify(twoSum([2, 7, 11, 15], 9)));", "cpp": "#include <iostream>\n#include <vector>\n#include <unordered_map>\nusing namespace std;\n\nvector<int> twoSum(vector<int>& nums, int target) {\n    // Write your solution here\n    return {};\n}\n\nint main() {\n    cout << \"[0, 1]\" << endl;\n    return 0;\n}", "java": "import java.util.*;\n\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        // Write your solution here\n        return new int[]{0, 1};\n    }\n    public static void main(String[] args) {\n        System.out.println(\"[0, 1]\");\n    }\n}"}',
    '["A brute force search checks every pair in O(N^2) time. Can we do better using auxiliary storage?", "Can we use a hash map to check whether the complement (target - current) exists in O(1) time?", "Iterate through the array once: if (target - num) is in your hash map, return [map[target - num], current_index]. Otherwise store num -> index."]')
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_problems (id, title, difficulty, category, description, constraints, examples, starter_code, hints)
VALUES ('valid-parentheses',
    'Valid Parentheses',
    'Easy',
    'Stack',
    'Given a string `s` containing just the characters ''('', '')'', ''{'', ''}'', ''['' and '']'', determine if the input string is valid.

An input string is valid if open brackets are closed by the same type of brackets and in the correct order.',
    '["1 <= s.length <= 10^4", "s consists of parentheses only ''()[]{}''."]',
    '[{"input": "s = \"()[]{}\"", "output": "true", "explanation": "All bracket pairs open and close symmetrically."}, {"input": "s = \"(]\"", "output": "false", "explanation": "Mismatched bracket closing."}]',
    '{"python": "def isValid(s: str) -> bool:\n    # Write your solution here\n    pass\n\nprint(str(isValid(\"()[]{}\")).lower())", "javascript": "function isValid(s) {\n    // Write your solution here\n}\n\nconsole.log(isValid(\"()[]{}\"));", "cpp": "#include <iostream>\n#include <string>\n#include <stack>\nusing namespace std;\n\nbool isValid(string s) {\n    return true;\n}\n\nint main() {\n    cout << \"true\" << endl;\n    return 0;\n}", "java": "public class Solution {\n    public static boolean isValid(String s) {\n        return true;\n    }\n    public static void main(String[] args) {\n        System.out.println(\"true\");\n    }\n}"}',
    '["Consider what data structure naturally operates in Last-In, First-Out (LIFO) order.", "Push opening brackets onto a stack. When an closing bracket appears, check if the stack top matches.", "Remember edge cases: what if closing brackets appear when the stack is empty, or brackets remain open at the end?"]')
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_problems (id, title, difficulty, category, description, constraints, examples, starter_code, hints)
VALUES ('longest-substring',
    'Longest Substring Without Repeating Characters',
    'Medium',
    'Sliding Window',
    'Given a string `s`, find the length of the longest substring without duplicate characters.',
    '["0 <= s.length <= 5 * 10^4", "s consists of English letters, digits, symbols and spaces."]',
    '[{"input": "s = \"abcabcbb\"", "output": "3", "explanation": "The answer is \"abc\", with the length of 3."}]',
    '{"python": "def lengthOfLongestSubstring(s: str) -> int:\n    # Write your solution here\n    pass\n\nprint(lengthOfLongestSubstring(\"abcabcbb\"))", "javascript": "function lengthOfLongestSubstring(s) {\n    // Write your solution here\n}\n\nconsole.log(lengthOfLongestSubstring(\"abcabcbb\"));", "cpp": "#include <iostream>\n#include <string>\nusing namespace std;\n\nint lengthOfLongestSubstring(string s) {\n    return 3;\n}\n\nint main() {\n    cout << 3 << endl;\n    return 0;\n}", "java": "public class Solution {\n    public static int lengthOfLongestSubstring(String s) {\n        return 3;\n    }\n    public static void main(String[] args) {\n        System.out.println(3);\n    }\n}"}',
    '["Can we maintain a sliding window `[left, right]` where all characters inside are unique?", "Use a set or map to track characters and their most recent indices.", "When a duplicate is encountered, slide the left pointer past the previous index of that character."]')
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT 'dcb33b6f-4922-5042-a3d7-f3ab59cd039a', 'two-sum', '[2, 7, 11, 15]
9', '[0, 1]', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'two-sum'
      AND existing.input_data = '[2, 7, 11, 15]
9'
      AND existing.expected_output = '[0, 1]'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT 'b9d21a22-9bfc-522d-873e-255c93592bc1', 'two-sum', '[3, 2, 4]
6', '[1, 2]', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'two-sum'
      AND existing.input_data = '[3, 2, 4]
6'
      AND existing.expected_output = '[1, 2]'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT 'be539a0c-59a5-5e5f-97b4-3862c4cca817', 'two-sum', '[3, 3]
6', '[0, 1]', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'two-sum'
      AND existing.input_data = '[3, 3]
6'
      AND existing.expected_output = '[0, 1]'
      AND existing.is_hidden = TRUE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT '14464328-905e-57d4-98c4-92eb2800437e', 'valid-parentheses', '()[]{}', 'true', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'valid-parentheses'
      AND existing.input_data = '()[]{}'
      AND existing.expected_output = 'true'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT 'eb119a6c-4ce9-5d29-9aef-b16562a16497', 'valid-parentheses', '(]', 'false', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'valid-parentheses'
      AND existing.input_data = '(]'
      AND existing.expected_output = 'false'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT '2430f62f-0b0d-5f7b-853d-18eb0f028b59', 'valid-parentheses', '([)]', 'false', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'valid-parentheses'
      AND existing.input_data = '([)]'
      AND existing.expected_output = 'false'
      AND existing.is_hidden = TRUE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT '2616cc3c-c3bf-5cee-9f53-ba6ef47fd169', 'longest-substring', 'abcabcbb', '3', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'longest-substring'
      AND existing.input_data = 'abcabcbb'
      AND existing.expected_output = '3'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT 'eeb0a16d-078b-5915-b3ab-c3ac90bf1219', 'longest-substring', 'bbbbb', '1', FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'longest-substring'
      AND existing.input_data = 'bbbbb'
      AND existing.expected_output = '1'
      AND existing.is_hidden = FALSE
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO coding_test_cases (id, problem_id, input_data, expected_output, is_hidden)
SELECT '9b488902-a2f0-5c83-80ea-b81d2d1fc9e9', 'longest-substring', 'pwwkew', '3', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM coding_test_cases existing
    WHERE existing.problem_id = 'longest-substring'
      AND existing.input_data = 'pwwkew'
      AND existing.expected_output = '3'
      AND existing.is_hidden = TRUE
)
ON CONFLICT (id) DO NOTHING;

COMMIT;
