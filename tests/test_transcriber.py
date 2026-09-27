from app.ai.transcriber import clean_transcript


def test_whisper_hallucinations_are_removed():
    text = "Варю аргоном пять лет. Продолжение следует... Субтитры сделал DimaTorzok"
    assert clean_transcript(text) == "Варю аргоном пять лет."


def test_normal_speech_is_untouched():
    text = "Спасибо, готов выйти в понедельник."
    assert clean_transcript(text) == text
