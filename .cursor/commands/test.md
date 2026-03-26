# Test Command

Execute tests and record results with AI Agent

## Purpose (Goal)
- Verify the correctness of implemented code
- Capture and store raw test evidence
- Generate a structured test report for review
- Provide review notes and improvement points before creating a PR  

## Parameters
- **`issue_url`** (preferred): Full GitHub issue URL. Derive owner, repo, issue_number from URL; doc path = `docs/issues/{repo}/{issue_number}/` (**repo** = short repo name).
- `issue_number` (optional): Issue number in current repo; if omitted, auto-detect from nearest doc.
- `output_path` (optional): Output directory path (defaults to current directory)

## Workflow Position
- This command should be run **after `/dev` (development)** and **before `/pr` (commit and pull request creation)**

## Critical Rules
**⛔ ABSOLUTE PROHIBITION: DO NOT EXECUTE ANY GIT COMMIT COMMANDS ⛔**
- NEVER run `git commit` in any form
- NEVER run `git add . && git commit`
- NEVER suggest or execute commit operations
- All changes MUST remain uncommitted at this stage

---

## Instructions for AI Agent

1. **Determine Issue Number and Doc Path** (doc path = `docs/issues/{repo}/{issue_number}/`, **repo** = short repo name)
   - If `issue_url` is provided: Extract `owner`, `repo`, `issue_number` from URL. Use `--repo {owner}/{repo}` with any GitHub CLI calls.
   - If `issue_number` (plain number) is provided: Use current repository: run `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo`.
   - If both are omitted: Find most recently modified `docs/issues/*/*/issue.md`; from path get `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` for gh calls.
   - Verify that `docs/issues/{repo}/{issue_number}/issue.md` exists

2. **Analyze Project Structure**
   - Identify test framework (Jest, Mocha, pytest, etc.)
   - Detect test file locations

3. **Execute Test Suite**
   - **If testable code exists**: Run appropriate test commands based on the framework
   - **If no testable code (documentation, configuration, etc.)**: Skip test execution and proceed to manual review

4. **Record Results**
   - **If tests were executed**: Save raw outputs to `docs/issues/{repo}/{issue_number}/evidence/`
     (e.g., `test_output.log`, `coverage.json`, `test-results.json`)
     - **IMPORTANT**: Save to `docs/issues/{repo}/{issue_number}/evidence/` (root level), NOT under backend/
   - **If no tests were executed**: Document "No automated tests available" with manual review results
   - Create final structured report in `docs/issues/{repo}/{issue_number}/test.md`
   - **CRITICAL: NO TEST RESULT FALSIFICATION**: Record actual test results only - NEVER create fake or simulated test results

5. **Generate Report**
   - **If tests were executed**: Summarize total tests, passed, failed, and coverage
   - **If tests were executed**: List failed tests with error details
   - **If no tests were executed**: Conduct manual review of deliverables and document findings
   - **Compare Issue Requirements vs Implementation vs Test Results (or Manual Review)**
   - Provide comprehensive **review notes** with improvement suggestions
   - **If tests fail to run or produce no results**: Explicitly document "Tests failed to execute" or "No test results generated" - DO NOT create fake results

6. **Cross-Reference Analysis**
   - Read `docs/issues/{repo}/{issue_number}/issue.md` to understand requirements
   - Read `docs/issues/{repo}/{issue_number}/spec.md` to understand specifications (if exists)
   - Read `docs/issues/{repo}/{issue_number}/plan.md` to understand planned tasks
   - Read `docs/issues/{repo}/{issue_number}/dev.md` to understand implementation progress
   - **If tests were executed**: Compare actual test results against planned coverage goals
   - **If no tests were executed**: Compare deliverables against issue requirements through manual review

7. **Handle Failures**
   - Do NOT commit or fix here
   - Document failure causes and suspected issues in `test.md`
   - **If tests were executed**: Identify gaps between issue requirements and test coverage
   - **If no tests were executed**: Identify gaps between issue requirements and deliverables through manual review
   - **If test execution fails completely**: Document "Test execution failed" with error details - NEVER create fake test results

---

## Output Structure Example

```
docs/
└── issues/
    └── {repo}/
        └── {issue_number}/
            ├── issue.md
            ├── evidence/
            │   ├── test_output.log
            │   ├── coverage.json
            │   └── screenshot.png
            └── test.md
```

**IMPORTANT**: Evidence files must be saved to `docs/issues/{repo}/{issue_number}/evidence/` (root level), NOT under backend/

## `test.md` Template

**For Issues with Testable Code:**
```markdown
# Test Report for Issue #{issue_number}

## Summary
- Total Tests: 128
- Passed: 125
- Failed: 3
- Coverage: 87%
```

**For Issues without Testable Code (Documentation, Configuration, etc.):**
```markdown
# Review Report for Issue #{issue_number}

## Summary
- **Test Type**: Manual Review (No automated tests available)
- **Deliverables Reviewed**: [List of deliverables created]
- **Requirements Compliance**: [Assessment of compliance with issue requirements]

### Manual Review Results
- **Files Created/Modified**: [List of files created or modified]
- **Content Quality**: [Assessment of content quality and completeness]
- **Format Compliance**: [Assessment of format and structure compliance]
- **Requirements Coverage**: [Assessment of how well deliverables meet requirements]

## Requirements vs Implementation Analysis

### Issue Requirements (from issue.md)
- **Primary Goal**: [Summarize main requirement from issue]
- **Success Criteria**: [List acceptance criteria from issue]
- **Target Coverage**: [Coverage goals if specified]

### Planned Implementation (from plan.md)
- **Task 1**: [Task description] - ✅ Completed
- **Task 2**: [Task description] - ✅ Completed
- **Task 3**: [Task description] - ❌ Not completed

### Actual Implementation (from dev.md)
- **Completed Tasks**: [List of completed tasks]
- **Coverage Achieved**: [Actual coverage numbers] (if applicable)
- **Deliverables Created**: [List of deliverables created]

## Failures (if applicable)
**For Testable Code:**
1. `tests/services/userService.test.js` - "should create user with valid data"  
   Error: ValidationError: email must be unique

2. `tests/routes/projectRoute.test.js` - "GET /projects returns list"  
   Error: Timeout (response > 5000ms)

3. `tests/utils/dateHelper.test.js` - "formatDate handles null input"  
   Error: TypeError: Cannot read property 'toISOString' of null

**For Non-Testable Code:**
- **Missing Requirements**: [List any requirements not met]
- **Quality Issues**: [List any quality or format issues found]
- **Incomplete Deliverables**: [List any incomplete deliverables]

## Cross-Reference Analysis

### ✅ Requirements Met
- [List requirements that were successfully implemented and tested]

### ❌ Requirements Gap
- [List requirements that were not fully implemented or tested]

### 🔄 Implementation vs Plan
- **Planned**: [What was planned in plan.md]
- **Actual**: [What was actually implemented in dev.md]
- **Gap**: [Difference between plan and implementation]

### 📊 Coverage Analysis
**For Testable Code:**
- **Target Coverage**: [Coverage goals from issue/spec]
- **Achieved Coverage**: [Actual coverage from test results]
- **Gap**: [Coverage shortfall and areas needing attention]

**For Non-Testable Code:**
- **Requirements Coverage**: [How well deliverables cover the issue requirements]
- **Quality Assessment**: [Assessment of deliverable quality and completeness]
- **Gap**: [Areas where requirements are not fully met]

## Review Notes

### ✅ Strengths
- [List successful implementations and test achievements]

### 🔍 Areas for Improvement
**For Testable Code:**
- [ ] **Requirement Gap**: [Specific requirement not met]
- [ ] **Coverage Gap**: [Areas with low coverage and why]
- [ ] **Implementation Gap**: [Planned vs actual implementation differences]
- [ ] **Test Quality**: [Test quality issues or missing test scenarios]

**For Non-Testable Code:**
- [ ] **Requirement Gap**: [Specific requirement not met in deliverables]
- [ ] **Quality Gap**: [Areas where deliverable quality can be improved]
- [ ] **Implementation Gap**: [Planned vs actual implementation differences]
- [ ] **Content Quality**: [Content quality issues or missing information]

### 📋 Recommendations for PR
**For Testable Code:**
1. **Requirements Compliance**: [How well the implementation meets the original issue requirements]
2. **Test Coverage**: [Coverage analysis and recommendations]
3. **Code Quality**: [Code quality observations from test results]
4. **Future Improvements**: [Suggestions for future iterations]

**For Non-Testable Code:**
1. **Requirements Compliance**: [How well the deliverables meet the original issue requirements]
2. **Deliverable Quality**: [Quality assessment and recommendations]
3. **Content Completeness**: [Assessment of content completeness and accuracy]
4. **Future Improvements**: [Suggestions for future iterations or enhancements]
```
