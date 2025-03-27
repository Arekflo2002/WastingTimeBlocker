"""
Parsing logic that parses .ics fiels into a list of tasks.
Most of the logic was taken from: https://github.com/ics-py/ics-py
Only added value is to consider the RRULE attribute and to repeat the
task based on that rule.
"""

import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any, Optional, TypedDict

import attr
import requests
import tatsu.exceptions
from dateutil.rrule import rrulestr
from ics.grammar.contentline import contentlineParser
from ics.utils import iso_to_arrow, unescape_string

from BlockingApps.task import Task
from BlockingApps.utils import TZ_INFO

#### region: Full copy code from isc module

GRAMMAR = contentlineParser()


class Task_Args(TypedDict):
    title: str
    start_time: datetime
    end_time: datetime
    description: str
    repetition: Optional[str]


@attr.s(auto_exc=True)
class ParseError(Exception):
    line: str = attr.ib(default="")
    nr: int = attr.ib(default=-1)


class ContentLine:
    """
    Represents one property line.

    For example:

    ``FOO;BAR=1:YOLO`` is represented by

    ``ContentLine('FOO', {'BAR': ['1']}, 'YOLO'))``

    Args:

        name:   The name of the property (uppercased for consistency and
                easier comparison)
        params: A map name:list of values
        value:  The value of the property
    """

    def __init__(self, name: str, params: dict[str, list[str]] = {}, value: str = ""):
        self.name = name.upper()
        self.params = params
        self.value = value

    def __eq__(self, other):
        ret = (
            self.name == other.name
            and self.params == other.params
            and self.value == other.value
        )
        return ret

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        params_str = ""
        for pname in self.params:
            params_str += ";{}={}".format(pname, ",".join(self.params[pname]))
        return "{}{}:{}".format(self.name, params_str, self.value)

    def __repr__(self):
        return "<ContentLine '{}' with {} parameter{}. Value='{}'>".format(
            self.name,
            len(self.params),
            "s" if len(self.params) > 1 else "",
            self.value,
        )

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, item, *values):
        self.params[item] = [val for val in values]

    @classmethod
    def parse(cls, line, nr=-1):
        """Parse a single iCalendar-formatted line into a ContentLine"""
        if "\n" in line or "\r" in line:
            raise ValueError("ContentLine can only contain escaped newlines")
        try:
            ast = GRAMMAR.parse(line)
        except tatsu.exceptions.FailedToken:
            raise ParseError(line, nr)

        name = "".join(ast["name"])
        value = "".join(ast["value"])
        params = {}
        for param_ast in ast.get("params", []):
            param_name = "".join(param_ast["name"])
            param_values = ["".join(x["value"]) for x in param_ast["values"]]
            params[param_name] = param_values
        return cls(name, params, value)

    def clone(self):
        """Makes a copy of itself"""
        # dict(self.params) -> Make a copy of the dict
        return self.__class__(self.name, dict(self.params), self.value)


class Container(list):
    """
    Represents an iCalendar object.
    Contains a list of ContentLines or Containers.

    Args:

        name: the name of the object (VCALENDAR, VEVENT etc.)
        items: Containers or ContentLines
    """

    def __init__(self, name: str, *items: list[ContentLine]):
        super(Container, self).__init__(items)
        self.name = name

    def __str__(self):
        name = self.name
        ret = ["BEGIN:" + name]
        for line in self:
            ret.append(str(line))
        ret.append("END:" + name)
        return "\r\n".join(ret)

    def __repr__(self):
        return "<Container '{}' with {} element{}>".format(
            self.name, len(self), "s" if len(self) > 1 else ""
        )

    @classmethod
    def parse(cls, name, tokenized_lines):
        items = []
        for line in tokenized_lines:
            if line.name == "BEGIN":
                items.append(Container.parse(line.value, tokenized_lines))
            elif line.name == "END":
                if line.value != name:
                    raise ParseError(
                        "Expected END:{}, got END:{}".format(name, line.value)
                    )
                break
            else:
                items.append(line)
        return cls(name, *items)

    def clone(self):
        """Makes a copy of itself"""
        c = self.__class__(self.name)
        for elem in self:
            c.append(elem.clone())
        return c


#### endregion

#### region: Added logic for RRULE attribute


class Parser:
    """
    Containts all of the steps going from .isc
    file into the list of tasks
    """

    @classmethod
    def filter_task_by_today(cls, tasks: list[Task]) -> list[Task]:
        "Get only those tasks that are for today"
        today = datetime.now(TZ_INFO).date()
        return [
            task
            for task in tasks
            if task.start_time.date() == today or task.end_time.date() == today
        ]

    def _unfold_lines(self, physical_lines: Iterable, with_linenr=False) -> Any:
        if not isinstance(physical_lines, Iterable):
            raise ParseError("Parameter `physical_lines` must be an iterable")
        current_nr = -1
        current_line = ""
        for nr, line in enumerate(physical_lines):
            if len(line.strip()) == 0:
                continue
            elif not current_line:
                current_nr = nr
                current_line = line.strip("\r")
            elif line[0] in (" ", "\t"):
                current_line += line[1:].strip("\r")
            else:
                if with_linenr:
                    yield current_nr, current_line
                else:
                    yield current_line
                current_nr = nr
                current_line = line.strip("\r")
        if current_line:
            if with_linenr:
                yield current_nr, current_line
            else:
                yield current_line

    def _tokenize_line(self, unfolded_lines: Iterable) -> Any:
        for line in unfolded_lines:
            if isinstance(line, tuple):
                yield ContentLine.parse(line[1], line[0])
            else:
                yield ContentLine.parse(line)

    def _parse(self, tokenized_lines: Iterable) -> list:
        res = []
        for line in tokenized_lines:
            if line.name == "BEGIN":
                res.append(Container.parse(line.value, tokenized_lines))
            else:
                res.append(line)
        return res

    def _lines_to_container(self, lines: Iterable, linewise=True) -> list:
        if linewise:
            return self._parse(
                self._tokenize_line(self._unfold_lines(lines, with_linenr=True))
            )  # linewise
        else:
            return self._string_to_container(
                "\r\n".join(lines), linewise
            )  # full-string

    def _string_to_container(self, txt: str, linewise=True) -> list:
        if linewise:
            return self._lines_to_container(txt.split("\n"), linewise)  # linewise
        else:
            return self._parse(self._string_to_content_lines(txt))  # full-string

    def _string_to_content_lines(self, txt: str):
        txt = re.sub("\r?\n[ \t]", "", txt)
        ast = GRAMMAR.parse(txt, rule_name="full")
        for line in ast:
            line = line[0]
            name = "".join(line["name"])
            value = "".join(line["value"])
            params = {}
            for param_ast in line.get("params", []):
                param_name = "".join(param_ast["name"])
                param_values = ["".join(x["value"]) for x in param_ast["values"]]
                params[param_name] = param_values
            yield ContentLine(name, params, value)

    def _calendar_string_to_containers(
        self, string: str
    ) -> list[list[Container | ContentLine]]:
        if not isinstance(string, str):
            raise TypeError("Expecting a string")
        return self._string_to_container(string)

    def _container_to_task_args(self, container: Container) -> Task_Args:
        "Get the container and gather all of the argruments needed for task class"
        args: dict[str, Any] = {}
        for line in container:
            if not isinstance(line, ContentLine):
                continue
            if line.name == "SUMMARY":
                args["title"] = unescape_string(line.value)
            elif line.name == "DTSTART":
                args["start_time"] = iso_to_arrow(line).datetime  # type: ignore
            elif line.name == "DTEND":
                args["end_time"] = iso_to_arrow(line).datetime  # type: ignore
            elif line.name == "RRULE":
                args["repetition"] = line.value
            elif line.name == "DESCRIPTION":
                args["description"] = line.value

        # Create dict specific for args, so all errors happens here
        try:
            args_type: Task_Args = {
                "title": args["title"],
                "description": args.get("description", ""),
                "start_time": args["start_time"],
                "end_time": args["end_time"],
                "repetition": args.get("repetition", None),
            }
            return args_type
        except Exception as e:
            raise AttributeError(
                "Attribute needed to create task from file didin't exist"
            ) from e

    def _request_to_containers(self, url: str) -> list[Container | ContentLine]:
        "Make a reuquest to google calendar and transform it into container"
        response = requests.get(url)
        if response.status_code != 200:
            raise ConnectionError("Connection to google Calendar was not succesfull")
        containers = self._calendar_string_to_containers(response.text)[0]
        return containers

    def get_tasks(self, url_ics: str) -> list[Task]:
        """Main logic of this parser, that lets requestes become the tasks"""

        def _get_this_weeks_sunday() -> datetime:
            return datetime.now(TZ_INFO) + timedelta(
                days=(6 - datetime.today().weekday()) % 7 + 7
            )

        # Make a reuqest
        containers: list[Container | ContentLine] = self._request_to_containers(url_ics)

        # Get the args for task
        task_args_list: list[Task_Args] = []
        for content in containers:
            if isinstance(content, ContentLine):
                continue
            if len(content) <= 1:
                continue
            if content.name != "VEVENT":
                continue
            task_args_list.append(self._container_to_task_args(content))

        # Now, based on the gathered arguments for tasks, create a list of task
        task_list: list[Task] = []
        for task_args in task_args_list:
            if task_args.get("repetition", None) is None:
                # This is a single one day tasks, so just create it
                task_list.append(
                    Task(
                        **task_args,
                    )
                )
                continue

            # Repetition makes it harder, beacause the event has
            # to be repeated until it reaches our week end's
            start_time = task_args["start_time"]
            rule = rrulestr(task_args["repetition"], dtstart=start_time)
            occurrences = rule.between(start_time, _get_this_weeks_sunday(), inc=True)
            task_list.extend(
                [
                    Task(
                        title=task_args["title"],
                        description=task_args["description"],
                        repetition=task_args["repetition"],
                        start_time=occ,
                        end_time=occ
                        + (task_args.get("end_time", start_time) - start_time),
                    )
                    for occ in occurrences
                ]
            )

        return task_list
