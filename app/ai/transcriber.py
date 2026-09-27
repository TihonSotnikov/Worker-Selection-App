import torch
from faster_whisper import WhisperModel

device = "cuda:0" if torch.cuda.is_available() else "cpu"
# device = "cpu"
dtype = torch.float16 if torch.cuda.is_available() else torch.float32
# dtype = torch.float32


class Transcriber:
    def __init__(self, model_name: str, *args, **kwargs):
        self._model = WhisperModel(model_name)
        # self._pipeline = pipeline(
        #     "automatic-speech-recognition",
        #     model=model_name,
        #     dtype=dtype,
        #     device=device,
        #     *args,
        #     **kwargs
        # )

    def __call__(self, *args, **kwds):
        return self._model.transcribe(*args, **kwds)
        # return self._pipeline(*args, **kwds)


# "deepdml/faster-whisper-large-v3-turbo-ct2"
# "medium"
