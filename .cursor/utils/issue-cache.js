/**
 * Issue Cache Utility
 * 
 * Provides optimized issue data retrieval by using cached issue.md files
 * instead of repeated GitHub API calls.
 * Supports cross-repository issue references via GitHub issue URLs.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Parse a GitHub issue reference (URL or plain number)
 * @param {string|number} input - GitHub issue URL or issue number
 * @returns {{ owner: string|null, repo: string|null, number: number }}
 */
function parseIssueUrl(input) {
  const str = String(input).trim();
  const urlMatch = str.match(/github\.com\/([^/]+)\/([^/]+)\/issues\/(\d+)/);
  if (urlMatch) {
    return { owner: urlMatch[1], repo: urlMatch[2], number: parseInt(urlMatch[3], 10) };
  }
  if (/^\d+$/.test(str)) {
    return { owner: null, repo: null, number: parseInt(str, 10) };
  }
  throw new Error(`Invalid issue reference: ${input}. Expected a GitHub issue URL or a plain issue number.`);
}

/**
 * Parse issue data from issue.md file
 * @param {string} issueFilePath - Path to issue.md file
 * @returns {Object} Parsed issue data
 */
function parseIssueFromMarkdown(issueFilePath) {
  try {
    const content = fs.readFileSync(issueFilePath, 'utf8');
    
    // Extract issue information from markdown
    const issueData = {
      title: '',
      body: '',
      labels: [],
      assignees: [],
      state: 'OPEN',
      createdAt: '',
      updatedAt: '',
      url: ''
    };

    // Parse title from first heading
    const titleMatch = content.match(/^# Issue #\d+: (.+)$/m);
    if (titleMatch) {
      issueData.title = titleMatch[1];
    }

    // Parse issue information section
    const infoSection = content.match(/## 📋 Issue情報[\s\S]*?(?=##|$)/);
    if (infoSection) {
      const info = infoSection[0];
      
      // Extract state
      const stateMatch = info.match(/- \*\*状態\*\*: (\w+)/);
      if (stateMatch) {
        issueData.state = stateMatch[1];
      }
      
      // Extract creation date
      const createdMatch = info.match(/- \*\*作成日時\*\*: (.+)/);
      if (createdMatch) {
        issueData.createdAt = createdMatch[1];
      }
      
      // Extract update date
      const updatedMatch = info.match(/- \*\*更新日時\*\*: (.+)/);
      if (updatedMatch) {
        issueData.updatedAt = updatedMatch[1];
      }
      
      // Extract URL
      const urlMatch = info.match(/- \*\*URL\*\*: (.+)/);
      if (urlMatch) {
        issueData.url = urlMatch[1].trim();
      }
    }

    // Extract repository from Context / Codebase Paths section
    const repoMatch = content.match(/^repository:\s*(.+)$/m);
    if (repoMatch) {
      issueData.repository = repoMatch[1].trim();
    } else if (issueData.url) {
      // Derive repository from URL as fallback
      const urlRepo = issueData.url.match(/github\.com\/([^/]+\/[^/]+)\/issues/);
      if (urlRepo) {
        issueData.repository = urlRepo[1];
      }
    }

    // Extract body from issue details section
    const detailsSection = content.match(/## 📝 Issue詳細([\s\S]*?)(?=## 🎯|$)/);
    if (detailsSection) {
      issueData.body = detailsSection[1].trim();
    }

    return issueData;
  } catch (error) {
    console.error(`Error parsing issue file ${issueFilePath}:`, error.message);
    return null;
  }
}

/**
 * Get issue data with caching strategy
 * @param {number} issueNumber - GitHub issue number
 * @param {string|null} [repoFullName] - Repository in "owner/repo" format (optional; uses current repo if omitted)
 * @returns {Object} Issue data object
 */
function getIssueData(issueNumber, repoFullName) {
  const issueFile = path.join(process.cwd(), `docs/issues/${issueNumber}/issue.md`);
  
  // First try: Use cached local file
  if (fs.existsSync(issueFile)) {
    console.log(`📋 Using cached issue data from: docs/issues/${issueNumber}/issue.md`);
    const cachedData = parseIssueFromMarkdown(issueFile);
    if (cachedData) {
      return cachedData;
    }
    console.log('⚠️  Failed to parse cached file, falling back to GitHub API...');
  }
  
  // Fallback: GitHub API call
  const repoLabel = repoFullName ? ` (${repoFullName})` : ' (current repo)';
  console.log(`🌐 Fetching issue #${issueNumber}${repoLabel} from GitHub API...`);
  try {
    const repoFlag = repoFullName ? ` --repo ${repoFullName}` : '';
    const result = execSync(
      `gh issue view ${issueNumber}${repoFlag} --json title,body,labels,assignees,state,createdAt,updatedAt,url`,
      { encoding: 'utf8' }
    );
    return JSON.parse(result);
  } catch (error) {
    console.error(`Error fetching issue #${issueNumber} from GitHub:`, error.message);
    throw new Error(`Failed to retrieve issue #${issueNumber} data`);
  }
}

/**
 * Auto-detect the most recent issue number and its repository metadata
 * @returns {{ number: number, repository: string|null }} Most recent issue number with optional repo
 */
function detectLatestIssueNumber() {
  const issuesDir = path.join(process.cwd(), 'docs/issues');
  
  if (!fs.existsSync(issuesDir)) {
    throw new Error('No issues directory found. Please run /issue command first.');
  }
  
  const issueDirs = fs.readdirSync(issuesDir)
    .filter(dir => {
      const dirPath = path.join(issuesDir, dir);
      return fs.statSync(dirPath).isDirectory() && /^\d+$/.test(dir);
    })
    .map(dir => ({
      number: parseInt(dir, 10),
      path: path.join(issuesDir, dir),
      mtime: fs.statSync(path.join(issuesDir, dir)).mtime
    }))
    .sort((a, b) => b.mtime - a.mtime);
  
  if (issueDirs.length === 0) {
    throw new Error('No issue directories found. Please run /issue command first.');
  }

  const latest = issueDirs[0];

  // Try to read repository metadata from issue.md
  const issueFilePath = path.join(latest.path, 'issue.md');
  let repository = null;
  if (fs.existsSync(issueFilePath)) {
    const issueData = parseIssueFromMarkdown(issueFilePath);
    repository = issueData && issueData.repository ? issueData.repository : null;
  }

  return { number: latest.number, repository };
}

/**
 * Get issue data with auto-detection support.
 * Accepts a plain issue number, a GitHub issue URL, or undefined (auto-detect from docs/issues/).
 * @param {number|string|undefined} issueRef - Issue number, GitHub issue URL, or undefined for auto-detect
 * @returns {Object} Issue data with issueNumber and optional repository fields
 */
function getIssueDataWithAutoDetection(issueRef) {
  let issueNumber;
  let repository = null;

  if (issueRef) {
    const parsed = parseIssueUrl(issueRef);
    issueNumber = parsed.number;
    if (parsed.owner && parsed.repo) {
      repository = `${parsed.owner}/${parsed.repo}`;
    }
  } else {
    const detected = detectLatestIssueNumber();
    issueNumber = detected.number;
    repository = detected.repository;
  }

  const issueData = getIssueData(issueNumber, repository);

  return {
    issueNumber,
    repository,
    ...issueData
  };
}

module.exports = {
  parseIssueUrl,
  parseIssueFromMarkdown,
  getIssueData,
  detectLatestIssueNumber,
  getIssueDataWithAutoDetection
};
