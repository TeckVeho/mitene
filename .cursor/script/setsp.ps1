param(
    [Parameter(Mandatory = $true)]
    [string]$IssueUrl,
    [Parameter(Mandatory = $true)]
    [string]$SpValue
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

Write-Host "Target Issue: $owner/$repo#$issue_number"
Write-Host "SP Value to Set: $SpValue"
Write-Host ""

# --- Get issue project info ---
$issueQuery = @'
query($owner:String!, $repo:String!, $issue_number:Int!) {
  repository(owner:$owner, name:$repo) {
    issue(number:$issue_number) {
      id
      projectItems(first: 10) {
        nodes {
          id
          project {
            id
            title
          }
        }
      }
    }
  }
}
'@

$issueResponse = gh api graphql `
    -f owner=$owner `
    -f repo=$repo `
    -F issue_number=$issue_number `
    -f query="$issueQuery" | ConvertFrom-Json

$projectItems = $issueResponse.data.repository.issue.projectItems.nodes
if (-not $projectItems) { Write-Host "No project found."; exit 0 }

foreach ($item in $projectItems) {
    $projectId = $item.project.id
    $projectTitle = $item.project.title
    $itemId = $item.id

    Write-Host "Project: $projectTitle"
    Write-Host "Project ID: $projectId"
    Write-Host "Item ID: $itemId"

    # --- Get project fields ---
    $fieldQuery = @'
query($project_id:ID!) {
  node(id:$project_id) {
    ... on ProjectV2 {
      fields(first:50) {
        nodes {
          ... on ProjectV2FieldCommon {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            dataType
            options { id name }
          }
        }
      }
    }
  }
}
'@

    $fieldResponse = gh api graphql -f project_id=$projectId -f query="$fieldQuery" | ConvertFrom-Json
    $fields = $fieldResponse.data.node.fields.nodes
    if ($fields.Count -eq 0) { continue }

    # --- Find SP-like field ---
    $spField = $fields | Where-Object {
        $normalized = ($_.name -replace '[^a-zA-Z0-9]', '').ToLower()
        $normalized -eq 'sp' -or
        $normalized -eq 'storypoint' -or
        $normalized -eq 'storypoints' -or
        $normalized.Contains('storypoint')
    } | Select-Object -First 1
    if (-not $spField) { Write-Host "No SP-like field."; continue }

    $fieldId = $spField.id
    $fieldType = $spField.dataType
    Write-Host "Found SP Field: $($spField.name) (Type: $fieldType, ID: $fieldId)"

    # --- Prepare mutation and variables ---
    $mutation = ""
    $variables = @{}

    switch ($fieldType) {

        # ---------------------------
        # NUMBER type (Float!)
        # ---------------------------
        "NUMBER" {
            $mutation = @'
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $number: Float!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { number: $number }
    }
  ) { projectV2Item { id } }
}
'@
            $variables = @{
                projectId = $projectId
                itemId    = $itemId
                fieldId   = $fieldId
                number    = [double]$SpValue
            }
        }

        # ---------------------------
        # TEXT type (String!)
        # ---------------------------
        "TEXT" {
            $mutation = @'
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $text: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { text: $text }
    }
  ) { projectV2Item { id } }
}
'@
            $variables = @{
                projectId = $projectId
                itemId    = $itemId
                fieldId   = $fieldId
                text      = [string]$SpValue
            }
        }

        # ---------------------------
        # SINGLE_SELECT type (ID!)
        # ---------------------------
        "SINGLE_SELECT" {
            $option = $spField.options | Where-Object {
                $_.name -eq $SpValue
            }
            if (-not $option) {
                Write-Host "No matching option for '$SpValue'"
                Write-Host "Available options:"
                $spField.options | ForEach-Object { Write-Host " - $($_.name)" }
                continue
            }

            $mutation = @'
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId
      itemId: $itemId
      fieldId: $fieldId
      value: { singleSelectOptionId: $optionId }
    }
  ) { projectV2Item { id } }
}
'@
            Write-Host "Selected single select option: $($option.name) ($($option.id))"
            $variables = @{
                projectId = $projectId
                itemId    = $itemId
                fieldId   = $fieldId
                optionId  = $option.id
            }
        }

        default { Write-Host "Unsupported type: $fieldType"; continue }
    }

    # --- Save JSON payload safely (UTF-8 no BOM) ---
    $payload = @{
        query = $mutation
        variables = $variables
    } | ConvertTo-Json -Depth 5 -Compress

    $tmpFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tmpFile, $payload, (New-Object System.Text.UTF8Encoding($false)))

    Write-Host "Running mutation..."
    $result = gh api graphql --input $tmpFile
    Remove-Item $tmpFile -Force

    Write-Host $result
    Write-Host "Mutation finished."
    Write-Host ""
}
