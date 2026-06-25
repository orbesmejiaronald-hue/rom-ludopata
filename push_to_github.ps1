$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;" + $env:PATH

# El token se pasa como variable de entorno GITHUB_TOKEN
$token = $env:GITHUB_TOKEN
$remoteUrl = "https://$token@github.com/orbesmejiaronald-hue/rom-ludopata.git"

Set-Location "C:\Users\ronald\Desktop\ROM SPORT"

git add .
git commit -m "Update: remove secrets from scripts"
git remote set-url origin $remoteUrl
git push -u origin main --force

Write-Host "PUSH COMPLETADO"
