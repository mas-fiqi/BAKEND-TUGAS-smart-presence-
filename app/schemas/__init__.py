# Minimal schema package exports.
# Only export fallback schemas to avoid importing missing files.
from .fallback import FallbackIn, FallbackOut

__all__ = ["FallbackIn", "FallbackOut"]
