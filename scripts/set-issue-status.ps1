# Usage: .\scripts\set-issue-status.ps1 -Issue 22 -Status "In Progress"
# Valid statuses: Todo, "In Progress", "In Review", Done
param(
    [Parameter(Mandatory)][int]$Issue,
    [Parameter(Mandatory)][string]$Status
)

$PROJECT_ID   = "PVT_kwHOALMvNM4BaahH"
$FIELD_ID     = "PVTSSF_lAHOALMvNM4BaahHzhVSUB8"
$STATUS_IDS   = @{
    "Todo"        = "f75ad846"
    "In Progress" = "47fc9ee4"
    "In Review"   = "ccc97365"
    "Done"        = "98236657"
}

$optionId = $STATUS_IDS[$Status]
if (-not $optionId) {
    Write-Error "Unknown status '$Status'. Valid: $($STATUS_IDS.Keys -join ', ')"
    exit 1
}

$items = gh project item-list 2 --owner philipreese --format json | ConvertFrom-Json
$item = $items.items | Where-Object { $_.content.number -eq $Issue }
if (-not $item) {
    Write-Error "Issue #$Issue not found in project board"
    exit 1
}

gh project item-edit --project-id $PROJECT_ID --id $item.id --field-id $FIELD_ID --single-select-option-id $optionId
Write-Host "Issue #$Issue moved to '$Status'"
