# ============================================
# BLOQUEIO INSTANTÂNEO (ONE SHOT)
# ============================================

Set-ExecutionPolicy Bypass -Scope Process -Force

# Aplica configuração leve (sem auto-lock agressivo)
$LoadedUsers = Get-ChildItem Registry::HKEY_USERS |
Where-Object {
    $_.PSChildName -match '^S-1-5-21-' -and
    $_.PSChildName -notmatch '_Classes$'
}

foreach ($User in $LoadedUsers) {

    $DesktopKey = "Registry::HKEY_USERS\$($User.PSChildName)\Control Panel\Desktop"

    New-ItemProperty -Path $DesktopKey -Name ScreenSaveActive -Value "1" -Force | Out-Null
    New-ItemProperty -Path $DesktopKey -Name ScreenSaverIsSecure -Value "1" -Force | Out-Null

    # timeout seguro (evita lock automático agressivo)
    New-ItemProperty -Path $DesktopKey -Name ScreenSaveTimeOut -Value "600" -Force | Out-Null
}

# atualiza sessão
rundll32.exe user32.dll,UpdatePerUserSystemParameters

# bloqueio imediato único
Start-Sleep -Milliseconds 300
rundll32.exe user32.dll,LockWorkStation