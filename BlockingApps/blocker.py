"""Implements the blocking for these systems: Linux, darwin, Windows"""

import platform
import subprocess
import time

from abc import ABC, abstractmethod

from typing import Literal, cast, TypedDict


# To block prints from the subprocesses
class SUBPROCESS_PRINT_BLOCKER_TYPE(TypedDict):
    stdout: int
    stderr: int


SUBPROCESS_PRINT_BLOCKER: SUBPROCESS_PRINT_BLOCKER_TYPE = {
    "stdout": subprocess.DEVNULL,
    "stderr": subprocess.DEVNULL,
}


class IBlocker(ABC):
    """Basic class that acts as interface for future blocker class."""

    @abstractmethod
    def block_apps(self, apps_to_block: list[str]) -> None:
        """
        This funcion block all of the apps that
        are supposed to be block for current task
        """
        raise NotImplementedError("Abstract class")

    @abstractmethod
    def block_websites(self, websites_to_block: list[str]) -> None:
        """
        This function block all of the websites for
        current task that is on the schedule
        """
        raise NotImplementedError("Abstract class")

    @abstractmethod
    def unblock_website(self, websites_to_unblock: list[str]) -> None:
        """
        After the task is done, then ublock all of the
        previously blocked websites
        """
        raise NotImplementedError("Abstract class")


class Windows_Blocker(IBlocker):
    """Implements blocking websites and apps on windows"""

    def __init__(self) -> None:
        self._system = "windows"
        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        self.redirect_ip = "127.0.0.1"

    def block_apps(self, apps_to_block: list[str]) -> None:
        """Force quit specified apps on Windows."""
        for app in apps_to_block:
            try:
                subprocess.run(
                    f"taskkill /IM {app}* /F", shell=True, **SUBPROCESS_PRINT_BLOCKER
                )
            except FileNotFoundError as e:
                raise SystemError("Can' use command on this system!") from e
            except Exception:
                continue  # No app to clsoe found

    def block_websites(self, websites_to_block: list[str]) -> None:
        """Modify the Windows hosts file to block access to specific websites."""
        try:
            with open(self.hosts_path, "a") as hosts_file:
                for site in websites_to_block:
                    print(site)
                    hosts_file.write(f"\n{self.redirect_ip} {site}")
            # Flush DNS and reset the ipconfig for these changes to take place
            subprocess.run("ipconfig /flushdns", **SUBPROCESS_PRINT_BLOCKER)
            subprocess.run("ipconfig /release", **SUBPROCESS_PRINT_BLOCKER)
            time.sleep(0.5)
            subprocess.run("ipconfig /renew", **SUBPROCESS_PRINT_BLOCKER)
            time.sleep(3)
        except Exception as e:
            print(f"Failed to modify hosts file: {e}")

    def unblock_website(self, websites_to_unblock: list[str]) -> None:
        try:
            with open(self.hosts_path, "r") as file:
                lines = file.readlines()
            with open(self.hosts_path, "w") as file:
                for line in lines:
                    if not any(site in line for site in websites_to_unblock):
                        file.write(line)
            # Flush DNS
            subprocess.run("ipconfig /flushdns", **SUBPROCESS_PRINT_BLOCKER)
        except Exception as e:
            print(f"Failed to modify hosts file: {e}")


class MAC_Blocker(IBlocker):
    """Implements blocking websites and apps on MAC"""

    def __init__(self) -> None:
        self._system = "MAC"
        self.hosts_path = "/etc/hosts"
        self.redirect_ip = "127.0.0.1"

    def block_apps(self, apps_to_block: list[str]) -> None:
        """Force quit the specified apps on macOS."""
        for app in apps_to_block:
            try:
                subprocess.run(
                    ["pkill", "-f", app], check=True, **SUBPROCESS_PRINT_BLOCKER
                )
            except FileNotFoundError:
                raise SystemError("Can't use pkill on your system!")
            except Exception:
                continue  # No process of that name found

    def block_websites(self, websites_to_block: list[str]) -> None:
        """
        Modify the /etc/hosts file to block access to specific websites.
        If website already exists there don't do anything
        """
        try:
            with open(self.hosts_path, "r+") as hosts_file:
                content = hosts_file.read()
                for site in websites_to_block:
                    if site in content:
                        continue
                    hosts_file.write(f"\n{self.redirect_ip} {site}")
            # Flush DNS
            subprocess.run(
                ["sudo", "dscacheutil", "-flushcache"], **SUBPROCESS_PRINT_BLOCKER
            )
            subprocess.run(
                ["sudo", "killall", "-HUP", "mDNSResponder"], **SUBPROCESS_PRINT_BLOCKER
            )
            subprocess.run("sudo ifconfig en0 down", **SUBPROCESS_PRINT_BLOCKER)
            time.sleep(0.5)
            subprocess.run("sudo ifconfig en0 up", **SUBPROCESS_PRINT_BLOCKER)
            time.sleep(3)
        except Exception as e:
            print(f"Failed to modify hosts file: {e}")

    def unblock_website(self, websites_to_unblock: list[str]) -> None:
        """Remove blocked websites from /etc/hosts."""
        try:
            with open(self.hosts_path, "r") as file:
                lines = file.readlines()
            with open(self.hosts_path, "w") as file:
                for line in lines:
                    if not any(site in line for site in websites_to_unblock):
                        file.write(line)
            # Flush DNS
            subprocess.run(
                ["sudo", "dscacheutil", "-flushcache"], **SUBPROCESS_PRINT_BLOCKER
            )
            subprocess.run(
                ["sudo", "killall", "-HUP", "mDNSResponder"], **SUBPROCESS_PRINT_BLOCKER
            )
        except Exception as e:
            print(f"Failed to modify hosts file: {e}")


class Blocker:
    """
    Represents blocking apps and websites on different system
    Avaiable system are:
    - Linux
    - Mac
    - Windows
    """

    SYSTEM_MAPPING: dict[str, type[IBlocker]] = {
        "windows": Windows_Blocker,
        "darwin": MAC_Blocker,
        "linux": MAC_Blocker,
    }

    def __init__(self) -> None:
        system = platform.system().lower()
        if system not in self.SYSTEM_MAPPING.keys():
            raise SystemError(
                f"This system({self._system_used}) is currently not supported"
            )
        self._system_used: Literal["windows", "linux", "darwin"] = cast(
            Literal["windows", "linux", "darwin"], system
        )
        self._specific_blocker: IBlocker = self.SYSTEM_MAPPING[self._system_used]()

    def block_apps(self, apps_to_block: list[str]) -> None:
        """
        This funcion block all of the apps that
        are passed to be block for current task
        """
        self._specific_blocker.block_apps(apps_to_block)

    def block_websites(self, websites_to_block: list[str]) -> None:
        """
        This function block all of the websites for
        current task that is on the schedule
        """
        self._specific_blocker.block_websites(websites_to_block)

    def unblock_websites(self, websites_to_unblock: list[str]) -> None:
        """
        This function unblock all of the previously
        blocked websites after the task is done
        """
        self._specific_blocker.unblock_website(websites_to_unblock)
