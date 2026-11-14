# Run from any working directory. The virtual environment is always project-local.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Project Python environment is missing. Follow the installation steps in README.md.'
}
& $projectPython -c 'import streamlit' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'Project Python cannot start or Streamlit is missing. Repair the project environment using README.md.'
}
& $projectPython -m streamlit run (Join-Path $PSScriptRoot 'streamlit_app.py')
