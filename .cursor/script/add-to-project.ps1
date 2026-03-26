<#
.SYNOPSIS
  Add a GitHub issue to a Project V2 (same project as parent).

.DESCRIPTION
  Uses GraphQL addProjectV2ItemById to add an issue to a project.
  Used by /breakdown to add child issues to the same project as the parent.

.PARAMETER IssueUrl
  Full GitHub issue URL (e.g. https://github.com/owner/repo/issues/123)

.PARAMETER ProjectId
  Project V2 node ID (from parent issue's projectItems). Required.

.EXAMPLE
  .\add-to-project.ps1 -IssueUrl "https://github.com/org/repo/issues/465" -ProjectId "PVT_xxx"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$IssueUrl,
    [Parameter(Mandatory = $true)]
    [string]$ProjectId
)

# --- Parse issue URL ---
if ($IssueUrl -match 'github\.com/([^/]+)/([^/]+)/issues/(\d+)') {
    $owner = $matches[1]
    $repo = $matches[2]
    $issue_number = $matches[3]
} else {
    Write-Host "Invalid issue URL format."
    exit 1
}

Write-Host "Adding issue $owner/$repo#$issue_number to project..."

# --- Get issue node ID (contentId) ---
$issueQuery = @'
query($owner:String!, $repo:String!, $issue_number:Int!) {
  repository(owner:$owner, name:$repo) {
    issue(number:$issue_number) {
      id
    }
  }
}
'@

$issueResponse = gh api graphql `
    -f owner=$owner `
    -f repo=$repo `
    -F issue_number=$issue_number `
    -f query="$issueQuery" | ConvertFrom-Json

$contentId = $issueResponse.data.repository.issue.id
if (-not $contentId) {
    Write-Host "Failed to get issue node ID."
    exit 1
}

# --- Add to project ---
$mutation = @'
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
    projectV2Item { id }
  }
}
'@

$payload = @{
    query = $mutation
    variables = @{
        projectId = $ProjectId
        contentId = $contentId
    }
} | ConvertTo-Json -Depth 5 -Compress

$tmpFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmpFile, $payload, (New-Object System.Text.UTF8Encoding($false)))

$result = gh api graphql --input $tmpFile
Remove-Item $tmpFile -Force

Write-Host "Added to project successfully."
