# Abra o PowerShell e execute o seguinte script

# Definir o nome do host do site
$site = 'www.funcionaldrinks.com.br'

# Criar um objeto de solicitação de web
$request = [Net.HttpWebRequest]::Create("https://$site")

# Definir a política de certificado SSL
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

# Obter a resposta
try {
    $response = $request.GetResponse()
} catch {
    Write-Host "Não foi possível conectar ao site: $site"
    return
}

# Obter o certificado SSL
$certificate = $request.ServicePoint.Certificate

# Obter as datas de validade do certificado
$validFrom = $certificate.GetEffectiveDateString()
$validTo = $certificate.GetExpirationDateString()

# Imprimir as datas de validade do certificado
Write-Host "Certificado para: $site"
Write-Host "Válido de: $validFrom"
Write-Host "Válido até: $validTo"

# Limpar a política de certificado SSL
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$null}
