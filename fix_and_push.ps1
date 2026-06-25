$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;" + $env:PATH
$token = $env:GITHUB_TOKEN
$remoteUrl = "https://$token@github.com/orbesmejiaronald-hue/rom-ludopata.git"

Set-Location "C:\Users\ronald\Desktop\ROM SPORT"

# Reescribir el historial eliminando el commit con el token
# Hacemos un soft reset al estado inicial y re-commiteamos sin el token
git reset --soft HEAD~1

# Agregar todo (ahora los scripts ya no tienen token)
git add .
git commit -m "Initial commit: ROM LUDOPATA 1.1 - Flask backend + Android app"

# Push forzado con la nueva historia limpia
git remote set-url origin $remoteUrl
git push -u origin main --force

Write-Host "PUSH EXITOSO"
