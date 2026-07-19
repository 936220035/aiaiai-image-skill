param(
    [ValidateSet('codex', 'claude', 'both')]
    [string]$Target = 'codex',
    [string]$CodexSkillRoot = '',
    [string]$ClaudeSkillRoot = ''
)

$ErrorActionPreference = 'Stop'
$repo = '936220035/aiaiai-image-skill'
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('aiaiai-image-skill-' + [guid]::NewGuid().ToString('N'))
$zipPath = Join-Path $tempRoot 'repo.zip'
$extractPath = Join-Path $tempRoot 'extract'

New-Item -ItemType Directory -Force -Path $tempRoot, $extractPath | Out-Null
try {
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/main.zip" -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
    $repoRoot = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
    if (-not $repoRoot) { throw 'Downloaded archive is empty.' }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $python) { throw 'Python 3 is required. Install Python and try again.' }
    $installArgs = @((Join-Path $repoRoot.FullName 'scripts/install_local.py'), '--target', $Target, '--mode', 'copy', '--force')
    if ($CodexSkillRoot) { $installArgs += @('--codex-skill-root', $CodexSkillRoot) }
    if ($ClaudeSkillRoot) { $installArgs += @('--claude-skill-root', $ClaudeSkillRoot) }
    & $python.Source @installArgs
    if ($LASTEXITCODE -ne 0) { throw 'Skill installation failed.' }
    Write-Host 'Installed. Restart Codex or Claude Code, then run configure to save your API key.' -ForegroundColor Green
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
