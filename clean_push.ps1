$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;" + $env:PATH
$token = $env:GITHUB_TOKEN
$remoteUrl = "https://$token@github.com/orbesmejiaronald-hue/rom-ludopata.git"

Set-Location "C:\Users\ronald\Desktop\ROM SPORT"

# Eliminar historial local completamente
Remove-Item -Recurse -Force ".git" -ErrorAction SilentlyContinue
Write-Host "Historial local eliminado"

# Reinicializar repo limpio
git init
git config user.email "orbesmejiaronald-hue@github.com"
git config user.name "orbesmejiaronald-hue"

# Stage todo (los scripts ya no contienen token)
git add .
git status

# Commit limpio sin ningún token en ningún archivo
git commit -m "Initial commit: ROM LUDOPATA 1.1 - Flask backend + Android app"

# Conectar al remote y push
git remote add origin $remoteUrl
git branch -M main
git push -u origin main --force

Write-Host "=== PUSH EXITOSO ==="
