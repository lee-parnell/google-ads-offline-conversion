from lingua import Language, LanguageDetectorBuilder

class LanguageDetector:
    def __init__(self) -> None:
        self.language_detector = LanguageDetectorBuilder.from_languages(*self.supported_languages).build()

    @property
    def supported_languages(self):
        return [Language.ENGLISH, Language.FRENCH, Language.GERMAN, Language.SPANISH, Language.TURKISH, Language.PORTUGUESE, Language.ARABIC, Language.ITALIAN]

    def detect_language(self, text_message):
        language = self.language_detector.detect_language_of(text_message)
        return language.name.capitalize() if language else "Undefined"
