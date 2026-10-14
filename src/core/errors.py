class TranslationPipelineError(Exception):
    """Raised when the translation pipeline cannot produce a valid output."""


class OutputWriteError(TranslationPipelineError):
    """The translation finished but writing the output file failed.

    Carries everything needed to salvage the run: the translated markdown,
    the target path and the validation report, so callers can surface the
    translation (e.g. in the UI) instead of losing it.
    """

    def __init__(self, message: str, *, output_text: str, output_path, validation, segments=None, translations=None) -> None:
        super().__init__(message)
        self.output_text = output_text
        self.output_path = output_path
        self.validation = validation
        self.segments = segments
        self.translations = translations
