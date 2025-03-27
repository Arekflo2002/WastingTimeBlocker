from datetime import datetime
from typing import Optional, TypedDict

from bs4 import BeautifulSoup

from BlockingApps.utils import TZ_INFO


class Blocked_Info(TypedDict):
    block_apps: list[str]
    block_websites: list[str]


class Task:
    "Representation of task from the calendar"

    def __init__(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str,
        repetition: Optional[str] = None,
    ) -> None:
        self.title: str = title
        self.start_time: datetime = start_time.astimezone(TZ_INFO)
        self.end_time: datetime = end_time.astimezone(TZ_INFO)
        self.repetition = repetition
        self.description: str = description

        self.blocking_info: Blocked_Info = self.extract_blocking_info(description)

    def _clean_description(self, text: str) -> str:
        """
        Removes HTML tags from a string while keeping the content and clean up the whole string
        for easier data extraction
        """
        return (
            BeautifulSoup(text, "html.parser")
            .get_text()
            .replace("<br>", "\\n")
            .replace("\r", "")
            .replace("\\n", " ")
            .replace("\\", " ")
        )

    def extract_blocking_info(self, desc: str) -> Blocked_Info:
        "Extract the info about, what app and websites shall be blocked"
        try:
            blocking_info = {"block_apps": [], "block_websites": []}
            desc = self._clean_description(desc).lower()

            # Get the text beetwen the BLOCKING blocks
            begin_index = desc.find("##blocking")
            end_index = desc.find("##blocking", begin_index + 1)
            desc_important_part = (
                desc[begin_index:end_index].replace("##blocking", "").strip()
            )
            if desc_important_part == "":
                raise ValueError("No blocking section on this task")

            # Get the apps to block
            desc_block_apps = (
                desc_important_part[
                    desc_important_part.find("block_apps:") : desc_important_part.find(
                        ";"
                    )
                ]
                .replace("block_apps:", "")
                .replace(";", "")
                .strip()
            )
            blocking_info["block_apps"] = [
                string.strip().lower() for string in desc_block_apps.split(",")
            ]

            # Get the websites to block
            first_index = desc_important_part.find("block_websites:")
            desc_block_websites = (
                desc_important_part[
                    first_index : desc_important_part.find(";", first_index)
                ]
                .replace("block_websites:", "")
                .replace(";", "")
                .strip()
            )
            blocking_info["block_websites"] = [
                string.strip().lower() for string in desc_block_websites.split(",")
            ]

            typed_return: Blocked_Info = {
                "block_apps": blocking_info.get("block_apps", []),
                "block_websites": blocking_info.get("block_websites", []),
            }
            return typed_return
        except:
            return {"block_apps": [], "block_websites": []}  # No blocking here

    def __str__(self) -> str:
        return f"Task: {self.title} | Start: {self.start_time} | End: {self.end_time} | Description: {self.description} | Repetition_rule: {self.repetition} | Blocking_info: {self.blocking_info}"

    def does_block_anything(self) -> bool:
        """
        This function checks, whether this task is
        supposed to be blocking anything. If yes then return True
        """
        if (
            self.blocking_info["block_apps"] != []
            and self.blocking_info["block_websites"] != []
        ):
            return True
        return False

    def is_active(self) -> bool:
        """Check if the task is currently active based on the current time."""
        now: datetime = datetime.now().astimezone(TZ_INFO)
        return self.start_time <= now <= self.end_time
