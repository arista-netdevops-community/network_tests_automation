# pylint: disable=E0401
# pylint: disable=E0611
# Pylint reports the following error, seems to be a false positive
# ************* Module anta.reporter.models
# anta/reporter/models.py:4:0: E0401: Unable to import 'rich.text' (import-error)
# anta/reporter/models.py:4:0: E0611: No name 'text' in module 'rich' (no-name-in-module)

"""Models related to anta.result_manager module."""

from pydantic import BaseModel, validator
from rich.text import Text

from ..result_manager.models import RESULT_OPTIONS


class ColorManager(BaseModel):
    """Color mangement for status report.

    Attributes:
        level (str): Test result value.
        color (str): Associated color.
    """
    level: str
    color: str

    @validator('level', allow_reuse=True)
    def name_must_be_in(cls, v: str) -> str:
        """
        Status validator

        Validate status is a supported one

        Args:
            v (str): User defined level

        Raises:
            ValueError: If level is unsupported

        Returns:
            str: level value
        """
        if v not in RESULT_OPTIONS:
            raise ValueError(f'must be one of {RESULT_OPTIONS}')
        return v

    def style_rich(self) -> Text:
        """
        Build a rich Text syntax with color

        Returns:
            Text: object with level string and its associated color.
        """
        return Text(self.level, style=self.color)

    def string(self) -> str:
        """
        Build an str with color code

        Returns:
            str: String with level and its associated color
        """
        return f'[{self.color}]{self.level}'
