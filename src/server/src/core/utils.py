"""Shared core helpers.

`generate_avatar` renders a deterministic DiceBear "glyphs" SVG seeded by the
account email and returns it as a base64 `data:` URI ready to drop into an
`<img src>`. It runs entirely on the server via the dicebear library — no HTTP
call, no file storage — so it works offline and needs no S3/media wiring.

It exists for accounts that have no photo: dispatch-created riders never sign up
through Firebase/mobile, so they arrive without an avatar. Accounts that DO have
a photo never call this (see Account.avatar_src).
"""

import base64
from functools import lru_cache
from importlib.resources import files

from dicebear import Avatar, Style

# Load the glyphs style definition once per process. The dicebear-styles package
# ships the same JSON the JS/PHP ports use, so output is byte-identical per seed.
_GLYPHS_STYLE = Style.from_json(
    files("dicebear_styles").joinpath("glyphs.json").read_text("utf-8")
)


@lru_cache(maxsize=512)
def generate_avatar(seed: str) -> str:
    """Return a `data:image/svg+xml;base64,…` URI for the glyph seeded by `seed`.

    `seed` is the account email, so the same email always yields the same image.
    Cached per process since generation is pure (no I/O) but not free, and the
    same accounts re-render across requests (e.g. the trips table).
    """
    svg = Avatar(_GLYPHS_STYLE, {"seed": seed}).to_string()
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
