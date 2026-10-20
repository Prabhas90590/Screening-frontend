$env:PATH = "$env:LOCALAPPDATA\Programs\nodejs;$env:PATH"
Set-Location -Path "$PSScriptRoot\frontend"
npm run dev

