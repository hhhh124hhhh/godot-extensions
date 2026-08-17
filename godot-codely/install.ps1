# Godot Codely - Editor plugin installer
#
# Two modes (answers "global or per-project?"):
#
# 1) Per-project install (recommended, most reliable)
#    Mount the addon into a Godot project's addons/ as a junction/symlink.
#    Only ONE source copy exists (godot-codely-addon/ next to this script);
#    all projects share the same real files, so editing once syncs everywhere.
#    This is "install once, visible in all projects" without depending on
#    Godot's version-floating global path.
#    powershell -File install.ps1 -Project "<你的Godot工程根>"
#
# 2) True global install (best-effort, version-dependent)
#    Local plugins (unlike AssetLib ones) have no "Install to Editor" button,
#    so you must place files manually into the editor config dir. Godot 4 mounts
#    that dir as res://addons/ for all projects, but the EXACT subpath floats
#    by version (candidates: [editor_data]/addons/ or
#    [editor_data]/editor_data/<ver>/addons/). On this machine
#    [editor_data] = %APPDATA%\Godot (= symlink -> D:/GodotData). After placing,
#    open editor Project Settings -> Plugins to see if it is listed; if not,
#    try the other candidate subpath.
#    powershell -File install.ps1 -Global
#
# Common params:
#    -WebView <path>   also mount a webview GDExtension (e.g. godot-cef) into addons/
#    -Force            if target exists, remove it first (default skips existing)
#
# Note: local EDR may block symlink creation; script auto-downgrades to copy
# (still works, but the project copy is no longer the single source of truth).

param(
  [string]$Project = "",
  [switch]$Global,
  [string]$WebView = "",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$addonSrc  = Join-Path $scriptDir "godot-codely-addon"

if (-not (Test-Path $addonSrc)) {
  Write-Error "Cannot find addon source dir: $addonSrc"
  exit 1
}

# Safely remove an existing target:
#   - reparse point (junction / symlink): use cmd /c rmdir to remove ONLY the
#     link point, never dive into / delete the real source directory
#   - normal directory: use Remove-Item -Recurse -Force
# Swallow any error and warn, never kill the whole script.
function Remove-TargetSafe {
  param([string]$path)
  try {
    $item = Get-Item $path -Force -ErrorAction Stop
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      cmd /c "rmdir `"$path`"" 2>$null
      Write-Host "[*] Removed link point (source untouched): $path"
    } else {
      Remove-Item $path -Recurse -Force -ErrorAction Stop
      Write-Host "[*] Removed directory: $path"
    }
  } catch {
    Write-Warning "Failed to remove $path : $($_.Exception.Message) ; continuing install."
  }
}

# Mount one addon copy into an addons/ root (junction preferred, symlink, then copy)
function Install-Addon {
  param(
    [string]$destRoot,
    [string]$label
  )
  $dest = Join-Path $destRoot "addons/godot-codely"
  if (Test-Path $dest) {
    if ($Force) {
      Remove-TargetSafe $dest
    } else {
      Write-Warning "$dest already exists, skipped (use -Force to overwrite)"
      return
    }
  }
  $parent = Split-Path -Parent $dest
  if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }

  $linked = $false
  # 1) Junction (same volume, no admin privilege, most stable)
  try {
    New-Item -ItemType Junction -Path $dest -Target $addonSrc -ErrorAction Stop | Out-Null
    Write-Host "[OK] Junction $label : $dest  ->  $addonSrc"
    $linked = $true
  } catch {
    # 2) SymbolicLink
    try {
      New-Item -ItemType SymbolicLink -Path $dest -Target $addonSrc -ErrorAction Stop | Out-Null
      Write-Host "[OK] Symlink $label : $dest  ->  $addonSrc"
      $linked = $true
    } catch {
      # 3) Copy fallback (EDR blocked links)
      Copy-Item -Path $addonSrc -Destination $dest -Recurse -Force
      Write-Host "[OK] Copy $label (links blocked, downgraded to copy): $dest"
    }
  }
  if (-not $linked) {
    Write-Host "     WARNING: this is a copy, not a link; editing godot-codely-addon/ will not auto-sync to this project."
  }
}

# Optional: also mount a webview GDExtension into addons/
function Install-WebView {
  param(
    [string]$destRoot,
    [string]$srcPath,
    [string]$label
  )
  if (-not (Test-Path $srcPath)) { Write-Warning "WebView source not found: $srcPath , skipped"; return }
  $leaf = Split-Path -Leaf $srcPath
  $dest = Join-Path $destRoot "addons/$leaf"
  if (Test-Path $dest) {
    if ($Force) { Remove-TargetSafe $dest } else { Write-Warning "$dest already exists, skipped"; return }
  }
  $parent = Split-Path -Parent $dest
  if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
  try {
    New-Item -ItemType Junction -Path $dest -Target $srcPath -ErrorAction Stop | Out-Null
    Write-Host "[OK] Junction webview $label : $dest  ->  $srcPath"
  } catch {
    try {
      New-Item -ItemType SymbolicLink -Path $dest -Target $srcPath -ErrorAction Stop | Out-Null
      Write-Host "[OK] Symlink webview $label : $dest  ->  $srcPath"
    } catch {
      Copy-Item -Path $srcPath -Destination $dest -Recurse -Force
      Write-Host "[OK] Copy webview $label (links blocked): $dest"
    }
  }
}

# ---- routing ----
if ($Global) {
  $editorData = Join-Path $env:APPDATA "Godot"
  $globalRoot = Join-Path $editorData "addons"
  Write-Host "==== True global install (editor config dir, best-effort) ===="
  Write-Host "Target root: $globalRoot"
  Write-Warning "Local plugins have no AssetLib 'Install to Editor' button; placed manually."
  Write-Warning "If Project Settings -> Plugins does not list it, try candidate subpath: [editor_data]/editor_data/<ver>/addons/"
  Install-Addon $globalRoot "global"
} elseif ($Project -ne "") {
  if (-not (Test-Path $Project)) {
    Write-Error "Project path does not exist: $Project"
    exit 1
  }
  Write-Host "==== Per-project install (junction preferred) ===="
  Write-Host "Target project: $Project"
  Install-Addon $Project "project"
} else {
  Write-Error "Must specify -Project <project path> or -Global"
  exit 1
}

if ($WebView -ne "") {
  $rootForWv = if ($Global) { Join-Path $env:APPDATA "Godot/addons" } else { $Project }
  Install-WebView $rootForWv $WebView $(if ($Global) { "global" } else { "project" })
}

Write-Host ""
Write-Host "==== Next steps ===="
Write-Host "1. Open the Godot 4.7.1 project (any project for global install)."
Write-Host "2. Project -> Project Settings -> Plugins -> enable 'Godot Codely'."
Write-Host "3. A 'Codely' panel appears in the right Dock: if a webview extension is installed it embeds dsh web(3080), otherwise it downgrades to an 'Open dsh web' button."
Write-Host "4. Make sure dsh web is running: dsh --profile web --patch .../dsh-godot-mount.patch.yml"
