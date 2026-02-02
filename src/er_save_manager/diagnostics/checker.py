"""Troubleshooting diagnostics checker for Elden Ring and save manager."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from er_save_manager.platform.utils import PlatformUtils


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""

    name: str
    status: str  # 'ok', 'warning', 'error', 'info'
    message: str
    fix_available: bool = False
    fix_action: str = ""


class TroubleshootingChecker:
    """Performs diagnostic checks for Elden Ring and the save manager."""

    # Suspicious files/folders that indicate piracy
    PIRACY_FOLDERS = ["_CommonRedist", "AdvGuide", "ArtbookOST"]

    PIRACY_FILES = [
        "dlllist.txt",
        "OnlineFix.ini",
        "OnlineFix64.dll",
        "steam_api64.rne",
        "steam_emu.ini",
        "winmm.dll",
        "dinput8.dll",
    ]

    # Problematic processes that can cause crashes
    PROBLEMATIC_PROCESSES = [
        "vgtray.exe",
        "Overwolf.exe",
        "RTSS.exe",  # RivaTuner Statistics Server
        "RTSSHooksLoader64.exe",
        "SystemExplorer.exe",
        "MSIAfterburner.exe",
        "Medal.exe",
        "SignalRgb.exe",
        "Discord.exe",  # overlay
        "GeForceExperience.exe",
        "ProcessLasso.exe",
    ]

    def __init__(
        self, game_folder: Path | None = None, save_file_path: Path | None = None
    ):
        """Initialize checker with optional game folder and save file path."""
        self.game_folder = Path(game_folder) if game_folder else None
        self.save_file_path = Path(save_file_path) if save_file_path else None

    def run_all_checks(self) -> list[DiagnosticResult]:
        """Run all diagnostic checks and return results."""
        results = []

        # Game installation checks
        results.append(self._check_game_installation())

        if self.game_folder and self.game_folder.exists():
            results.extend(self._check_piracy_indicators())
            results.append(self._check_game_executable())

        # Process checks
        results.extend(self._check_problematic_processes())
        results.append(self._check_steam_elevated())

        # Save file checks
        if self.save_file_path:
            results.extend(self._check_save_file_health())

        # Tool configuration checks
        results.extend(self._check_tool_configuration())

        return results

    def _check_game_installation(self) -> DiagnosticResult:
        """Check if Elden Ring is properly installed."""
        if not self.game_folder:
            return DiagnosticResult(
                name="Game Installation",
                status="warning",
                message="Game folder not specified",
                fix_available=False,
            )

        if not self.game_folder.exists():
            return DiagnosticResult(
                name="Game Installation",
                status="error",
                message=f"Game folder not found: {self.game_folder}",
                fix_available=False,
            )

        return DiagnosticResult(
            name="Game Installation",
            status="ok",
            message=f"Game folder found: {self.game_folder}",
        )

    def _check_game_executable(self) -> DiagnosticResult:
        """Check if eldenring.exe exists and validate size."""
        if not self.game_folder:
            return DiagnosticResult(
                name="Game Executable",
                status="info",
                message="Game folder not set",
            )

        exe_path = self.game_folder / "Game" / "eldenring.exe"
        if exe_path.exists():
            # Check file size - legitimate eldenring.exe is around 84964KB (82-87MB range)
            size_bytes = exe_path.stat().st_size
            size_kb = size_bytes // 1024
            size_mb = size_kb / 1024

            # Allow 82-87MB range for legitimate exe
            if 82000 <= size_kb <= 87000:
                return DiagnosticResult(
                    name="Game Executable",
                    status="ok",
                    message=f"eldenring.exe found ({size_mb:.1f}MB)",
                )
            else:
                return DiagnosticResult(
                    name="Game Executable",
                    status="warning",
                    message=f"eldenring.exe found but size is unusual ({size_mb:.1f}MB, expected ~83MB)",
                    fix_available=True,
                    fix_action="Delete the file and verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
                )
        else:
            return DiagnosticResult(
                name="Game Executable",
                status="error",
                message="eldenring.exe not found in Game folder",
                fix_available=True,
                fix_action="Verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
            )

    def _check_piracy_indicators(self) -> list[DiagnosticResult]:
        """Check for unsupported files and folders."""
        results = []

        if not self.game_folder or not self.game_folder.exists():
            return results

        # Check for suspicious folders
        found_folders = []
        for folder in self.PIRACY_FOLDERS:
            folder_path = self.game_folder / "Game" / folder
            if folder_path.exists():
                found_folders.append(folder)

        if found_folders:
            results.append(
                DiagnosticResult(
                    name="Unsupported Folders Detected",
                    status="warning",
                    message=f"Found unsupported folders: {', '.join(found_folders)}. These may cause issues.",
                    fix_available=False,
                )
            )

        # Check for piracy files
        found_files = []
        for file in self.PIRACY_FILES:
            file_path = self.game_folder / "Game" / file
            if file_path.exists():
                found_files.append(file)

        # Special check for steam_api64.dll size
        steam_api_path = self.game_folder / "Game" / "steam_api64.dll"
        if steam_api_path.exists():
            size_kb = steam_api_path.stat().st_size // 1024
            # Allow 258-266KB range (legitimate file can be reported as 258-266KB depending on calculation)
            if not (258 <= size_kb <= 266):
                found_files.append(
                    f"steam_api64.dll (modified - {size_kb}KiB instead of 260KiB)"
                )
        else:
            # steam_api64.dll is missing - critical error
            results.append(
                DiagnosticResult(
                    name="Critical File Missing",
                    status="error",
                    message="steam_api64.dll is missing from Game folder",
                    fix_available=True,
                    fix_action="Verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
                )
            )

        if found_files:
            results.append(
                DiagnosticResult(
                    name="Unsupported/Damaged Files Detected",
                    status="error",
                    message=f"Found unsupported files: {', '.join(found_files)}. These can cause issues.",
                    fix_available=True,
                    fix_action="Delete the unsupported files and verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    name="Game Integrity",
                    status="ok",
                    message="No issues detected",
                )
            )

        # Check regulation.bin size
        regulation_path = self.game_folder / "Game" / "regulation.bin"
        if regulation_path.exists():
            size_bytes = regulation_path.stat().st_size
            size_kb = size_bytes // 1024
            size_mb = size_kb / 1024

            # Allow 1.8-2.1MB range for legitimate regulation.bin (around 1989KB)
            if 1800 <= size_kb <= 2100:
                results.append(
                    DiagnosticResult(
                        name="Regulation File",
                        status="ok",
                        message=f"regulation.bin is valid ({size_mb:.1f}MB)",
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        name="Regulation File",
                        status="warning",
                        message=f"regulation.bin size is unusual ({size_mb:.1f}MB, expected ~1.9MB). May indicate modified game files.",
                        fix_available=True,
                        fix_action="Delete the file and verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
                    )
                )
        else:
            # regulation.bin is missing - critical error
            results.append(
                DiagnosticResult(
                    name="Critical File Missing",
                    status="error",
                    message="regulation.bin is missing from Game folder",
                    fix_available=True,
                    fix_action="Verify game integrity via Steam: Right-click Elden Ring > Properties > Installed Files > Verify",
                )
            )

        return results

    def _check_problematic_processes(self) -> list[DiagnosticResult]:
        """Check for running processes that can cause crashes."""
        results = []

        if not PlatformUtils.is_windows():
            return [
                DiagnosticResult(
                    name="Process Check",
                    status="info",
                    message="Process checking only available on Windows",
                )
            ]

        try:
            # Get list of running processes
            output = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            running_problematic = []
            for process_name in self.PROBLEMATIC_PROCESSES:
                if process_name.lower() in output.lower():
                    running_problematic.append(process_name)

            # Check Task Scheduler for Process Lasso (even if not running)
            process_lasso_scheduled = False
            try:
                schtasks_output = subprocess.check_output(
                    ["schtasks", "/query", "/fo", "LIST", "/v"],
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if "processlasso" in schtasks_output.lower():
                    process_lasso_scheduled = True
            except Exception:
                pass

            if running_problematic:
                results.append(
                    DiagnosticResult(
                        name="Problematic Processes Running",
                        status="warning",
                        message=f"Found processes that can cause crashes: {', '.join(running_problematic)}",
                        fix_available=True,
                        fix_action="Close these apps before playing, and disable them in Task Manager > Startup tab to prevent auto-launch.",
                    )
                )

            # Special warning for Process Lasso (running or scheduled)
            if (
                any("ProcessLasso" in p for p in running_problematic)
                or process_lasso_scheduled
            ):
                results.append(
                    DiagnosticResult(
                        name="Process Lasso Detected",
                        status="error",
                        message="Process Lasso can cause flashbang crashes on launch. Found in "
                        + (
                            "running processes and "
                            if any("ProcessLasso" in p for p in running_problematic)
                            else ""
                        )
                        + (
                            "Task Scheduler"
                            if process_lasso_scheduled
                            else "running processes"
                        ),
                        fix_available=True,
                        fix_action="1. Close Process Lasso if running\n2. Disable in Task Manager > Startup tab\n3. Remove from Task Scheduler > Task Scheduler Library (search for ProcessLasso tasks)",
                    )
                )

            if not running_problematic and not process_lasso_scheduled:
                results.append(
                    DiagnosticResult(
                        name="Process Check",
                        status="ok",
                        message="No problematic processes detected",
                    )
                )

        except Exception as e:
            results.append(
                DiagnosticResult(
                    name="Process Check",
                    status="warning",
                    message=f"Could not check processes: {e}",
                )
            )

        return results

    def _check_steam_elevated(self) -> DiagnosticResult:
        """Check if Steam is running with elevated (administrator) privileges."""
        if not PlatformUtils.is_windows():
            return DiagnosticResult(
                name="Steam Elevation Check",
                status="info",
                message="Steam elevation check only available on Windows",
            )

        try:
            # Use PowerShell to check if steam.exe is running elevated by checking process integrity level
            ps_script = """
            Add-Type -TypeDefinition @"
            using System;
            using System.Runtime.InteropServices;
            using System.Diagnostics;

            public class ProcessChecker {
                [DllImport("advapi32.dll", SetLastError=true)]
                public static extern bool OpenProcessToken(IntPtr ProcessHandle, uint DesiredAccess, out IntPtr TokenHandle);

                [DllImport("advapi32.dll", SetLastError=true)]
                public static extern bool GetTokenInformation(IntPtr TokenHandle, int TokenInformationClass, IntPtr TokenInformation, uint TokenInformationLength, out uint ReturnLength);

                [DllImport("kernel32.dll", SetLastError=true)]
                public static extern bool CloseHandle(IntPtr hObject);

                public static int CheckProcessElevation(int processId) {
                    IntPtr tokenHandle = IntPtr.Zero;
                    try {
                        Process process = Process.GetProcessById(processId);
                        if (OpenProcessToken(process.Handle, 0x0008, out tokenHandle)) {
                            uint returnLength;
                            IntPtr elevationResult = Marshal.AllocHGlobal(4);
                            try {
                                if (GetTokenInformation(tokenHandle, 20, elevationResult, 4, out returnLength)) {
                                    bool isElevated = Marshal.ReadInt32(elevationResult) != 0;
                                    return isElevated ? 1 : 0;
                                }
                            } finally {
                                Marshal.FreeHGlobal(elevationResult);
                            }
                        }
                        return 0;
                    } catch (System.ComponentModel.Win32Exception ex) {
                        // Access denied (error 5) means process is elevated
                        if (ex.NativeErrorCode == 5) {
                            return 1; // Elevated
                        }
                        return -1; // Unknown error
                    } catch (UnauthorizedAccessException) {
                        // Access denied means process is elevated
                        return 1;
                    } catch {
                        return -1;
                    } finally {
                        if (tokenHandle != IntPtr.Zero) {
                            CloseHandle(tokenHandle);
                        }
                    }
                }
            }
"@

            $steamProcesses = Get-Process -Name "steam" -ErrorAction SilentlyContinue
            if (-not $steamProcesses) {
                Write-Output "not_running"
                exit 1
            }

            $foundElevated = $false
            foreach ($proc in $steamProcesses) {
                try {
                    $result = [ProcessChecker]::CheckProcessElevation($proc.Id)
                    if ($result -eq 1) {
                        $foundElevated = $true
                        break
                    }
                } catch {
                    # Continue checking other processes
                }
            }

            if ($foundElevated) {
                Write-Output "elevated"
            } else {
                Write-Output "normal"
            }
            """

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
            )

            # Extract the last non-debug line from stdout
            stdout_lines = result.stdout.strip().split("\n")
            output = ""
            for line in reversed(stdout_lines):
                line_stripped = line.strip().lower()
                if line_stripped and not line_stripped.startswith("debug:"):
                    output = line_stripped
                    break

            if output == "not_running":
                return DiagnosticResult(
                    name="Steam Elevation Check",
                    status="info",
                    message="Steam is not currently running",
                )
            elif output == "elevated":
                # Steam is running as administrator - this can cause permission issues
                appdata_path = Path(os.getenv("APPDATA", "")) / "EldenRing"

                fix_message = """Steam is running with administrator privileges, which can cause file permission issues.

Recommended fixes (try in order):

1. Disable Steam Administrator Mode:
   - Exit Steam completely (right-click system tray icon > Exit)
   - Right-click Steam shortcut > Open file location
   - Right-click steam.exe > Properties > Compatibility tab
   - Uncheck "Run this program as an administrator"
   - Restart Steam normally

2. Take Ownership of Game & Save Folders (run these PowerShell commands as Admin):

Game folder ownership:
takeown /F "{game_folder}" /R /D Y
icacls "{game_folder}" /grant %USERNAME%:F /T

AppData folder ownership:
takeown /F "{appdata}" /R /D Y
icacls "{appdata}" /grant %USERNAME%:F /T

3. If issues persist:
   - Reinstall Steam (do NOT run as admin after reinstall)
   - Uninstall Elden Ring, delete game folder, reinstall
""".format(
                    game_folder=self.game_folder
                    if self.game_folder
                    else "C:\\Program Files (x86)\\Steam\\steamapps\\common\\ELDEN RING",
                    appdata=appdata_path,
                )

                return DiagnosticResult(
                    name="Steam Running as Administrator",
                    status="error",
                    message="Steam is running with elevated privileges. This can cause save file permission issues and crashes.",
                    fix_available=True,
                    fix_action=fix_message,
                )
            elif output == "normal":
                return DiagnosticResult(
                    name="Steam Elevation Check",
                    status="ok",
                    message="Steam is running with normal privileges",
                )
            else:  # unknown
                return DiagnosticResult(
                    name="Steam Elevation Check",
                    status="warning",
                    message="Could not determine if Steam is elevated (access denied)",
                )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                name="Steam Elevation Check",
                status="warning",
                message="Steam elevation check timed out",
            )
        except Exception as e:
            return DiagnosticResult(
                name="Steam Elevation Check",
                status="warning",
                message=f"Could not check Steam elevation: {e}",
            )

    def _check_save_file_health(self) -> list[DiagnosticResult]:
        """Check save file health and accessibility."""
        results = []

        if not self.save_file_path:
            return [
                DiagnosticResult(
                    name="Save File",
                    status="info",
                    message="No save file loaded",
                )
            ]

        # Check if file exists
        if not self.save_file_path.exists():
            return [
                DiagnosticResult(
                    name="Save File",
                    status="error",
                    message=f"Save file not found: {self.save_file_path}",
                )
            ]

        # Check read permissions
        if not os.access(self.save_file_path, os.R_OK):
            results.append(
                DiagnosticResult(
                    name="Save File Permissions",
                    status="error",
                    message="Cannot read save file - check file permissions",
                    fix_available=True,
                    fix_action="Run as administrator or check file permissions",
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    name="Save File Permissions",
                    status="ok",
                    message="Save file is readable",
                )
            )

        # Check file size (basic corruption check)
        file_size = self.save_file_path.stat().st_size
        if file_size < 1000:  # Save files should be much larger
            results.append(
                DiagnosticResult(
                    name="Save File Size",
                    status="error",
                    message=f"Save file is suspiciously small ({file_size} bytes) - may be corrupted",
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    name="Save File Size",
                    status="ok",
                    message=f"Save file size is normal ({file_size // 1024}KB)",
                )
            )

        # Check disk space
        if PlatformUtils.is_windows():
            try:
                import shutil

                total, used, free = shutil.disk_usage(self.save_file_path.parent)
                free_gb = free // (1024**3)
                if free_gb < 1:
                    results.append(
                        DiagnosticResult(
                            name="Disk Space",
                            status="warning",
                            message=f"Low disk space for backups: {free_gb}GB free",
                            fix_available=True,
                            fix_action="Free up disk space for save backups",
                        )
                    )
                else:
                    results.append(
                        DiagnosticResult(
                            name="Disk Space",
                            status="ok",
                            message=f"Sufficient disk space: {free_gb}GB free",
                        )
                    )
            except Exception:
                pass

        return results

    def _check_tool_configuration(self) -> list[DiagnosticResult]:
        """Check save manager tool configuration."""
        results = []

        # Check settings file
        from er_save_manager.ui.settings import get_settings

        try:
            get_settings()
            results.append(
                DiagnosticResult(
                    name="Settings",
                    status="ok",
                    message="Settings file is valid",
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    name="Settings",
                    status="error",
                    message=f"Error loading settings: {e}",
                    fix_available=True,
                    fix_action="Reset settings to defaults",
                )
            )

        return results
