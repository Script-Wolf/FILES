# Executar como Administrador para garantir permissões

# Função para limpar conteúdo de uma pasta, sem perguntas e forçando exclusão
function Clear-FolderContent {
    param (
        [string]$FolderPath
    )

    if (Test-Path $FolderPath) {
        Write-Host "Limpando: $FolderPath"
        Get-ChildItem -Path $FolderPath -Force -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                if ($_.PSIsContainer) {
                    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                } else {
                    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Ignora erros, como arquivos em uso
            }
        }
    } else {
        Write-Warning "Pasta não encontrada: $FolderPath"
    }
}

# Lista das pastas a limpar
$foldersToClear = @(
    "$env:windir\Temp",
    $env:TEMP,
    "$env:windir\Prefetch",
    "$env:USERPROFILE\AppData\Roaming\Microsoft\Windows\Recent"
)

# Limpa todas as pastas listadas
foreach ($folder in $foldersToClear) {
    Clear-FolderContent -FolderPath $folder
}

Write-Host "Limpeza completa."
