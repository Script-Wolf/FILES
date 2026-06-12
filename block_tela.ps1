# C:\Temp\block_tela.ps1
# Bloqueio de tela instantâneo + configuração automática para todos os usuários

# ============================================
# 1. PERMITIR EXECUÇÃO DE SCRIPTS
# ============================================
Set-ExecutionPolicy Unrestricted -Force

# ============================================
# 2. CONFIGURAR PROTETOR DE TELA PARA TODOS OS USUÁRIOS LOGADOS
# ============================================
$LoadedUsers = Get-ChildItem Registry::HKEY_USERS |
Where-Object {
    $_.PSChildName -match '^S-1-5-21-' -and
    $_.PSChildName -notmatch '_Classes$'
}

foreach ($User in $LoadedUsers) {

    $DesktopKey = "Registry::HKEY_USERS\$($User.PSChildName)\Control Panel\Desktop"

    New-ItemProperty -Path $DesktopKey -Name ScreenSaveActive -Value "1" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $DesktopKey -Name ScreenSaverIsSecure -Value "1" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $DesktopKey -Name ScreenSaveTimeOut -Value "5" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $DesktopKey -Name SCRNSAVE.EXE -Value "C:\Windows\System32\scrnsave.scr" -PropertyType String -Force | Out-Null
}

# ============================================
# 3. APLICAR CONFIGURAÇÕES DO SISTEMA
# ============================================
rundll32.exe user32.dll,UpdatePerUserSystemParameters

# ============================================
# 4. APLICAR POLÍTICAS DE GRUPO
# ============================================
gpupdate /target:user /force

# ============================================
# 5. BLOQUEAR A ESTAÇÃO IMEDIATAMENTE
# ============================================
rundll32.exe user32.dll,LockWorkStation