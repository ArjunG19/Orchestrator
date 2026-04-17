"""Prompt registry for loading and rendering LLM prompt templates."""

from pathlib import Path
from typing import Dict


class PromptRegistry:
    """Loads prompt templates from disk and renders them with variables.

    Templates use Python ``str.format_map()`` syntax, i.e. ``{variable_name}``
    placeholders.
    """

    def __init__(self, prompts_dir: str = "prompts") -> None:
        # Resolve relative to the project root (one level up from this file's
        # parent package directory).
        self.prompts_dir: Path = Path(__file__).resolve().parent.parent / prompts_dir

    def render(self, name: str, variables: Dict[str, str]) -> str:
        """Load the template identified by *name* and render it.

        Parameters
        ----------
        name:
            Stem of the template file (without ``.txt`` extension).
        variables:
            Mapping of placeholder names to their replacement values.

        Returns
        -------
        str
            The fully rendered prompt string.

        Raises
        ------
        FileNotFoundError
            If the template file does not exist.
        KeyError
            If *variables* is missing a key required by the template.
        """
        path = self.prompts_dir / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {name}.txt "
                f"(looked in {self.prompts_dir})"
            )
        template = path.read_text(encoding="utf-8")
        return template.format_map(variables)
