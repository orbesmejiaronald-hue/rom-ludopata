# Script de creación de repositorio en GitHub
# El token se pasa como variable de entorno GITHUB_TOKEN
$token = $env:GITHUB_TOKEN
$headers = @{
    Authorization = "token $token"
    Accept = "application/vnd.github+json"
    "Content-Type" = "application/json"
}
$body = @{
    name = "rom-ludopata"
    private = $false
    description = "ROM LUDOPATA - Sports Analytics App"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body -UseBasicParsing
    Write-Host "REPO CREADO EXITOSAMENTE"
    Write-Host $response.Content
} catch {
    $errContent = $_.Exception.Response
    if ($errContent) {
        $reader = New-Object System.IO.StreamReader($errContent.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Error del servidor: $responseBody"
    } else {
        Write-Host "Error: $_"
    }
}
