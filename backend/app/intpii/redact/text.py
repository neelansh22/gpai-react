from __future__ import annotations

from .core import Redactable, apply_text


class TextDoc(Redactable):
    def __init__(self, data: bytes, ext: str):
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            self.encoding = "utf-16"
        elif data.startswith(b"\xef\xbb\xbf"):
            self.encoding = "utf-8-sig"
        else:
            self.encoding = "utf-8"
        warnings: list[str] = []
        try:
            text = data.decode(self.encoding)
        except UnicodeDecodeError:
            self.encoding = "cp1252"
            try:
                text = data.decode(self.encoding)
            except UnicodeDecodeError:
                raise ValueError("could not decode the file as UTF-8, UTF-16 or Windows-1252")
            warnings.append("File is not valid UTF-8; read as Windows-1252 and will be written back the same way.")
        super().__init__("text", [text], "text/plain; charset=utf-8", ext, data, warnings)

    def render(self, spans, style):
        # Newlines are never normalised, so CRLF files stay CRLF.
        return apply_text(self.units[0], spans.get(0, []), style).encode(self.encoding)
