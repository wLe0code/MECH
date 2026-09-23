class _TTS:
    def convert_with_timestamps(self, **k):
        raise NotImplementedError("stub sin timestamps")

    def convert(self, **k):
        # Entrega un stream de bytes falsos (2 chunks chicos, como un mp3 real)
        def gen():
            yield b"\x00\x00\x01\x01"
            yield b"\xff\xfb\x00\x00"

        return gen()


class ElevenLabs:
    def __init__(self, api_key: str = ""):
        self.text_to_speech = _TTS()