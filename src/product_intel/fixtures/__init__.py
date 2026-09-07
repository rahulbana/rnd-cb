"""Bundled sample payloads for the pipeline.

Making this directory a regular package (rather than a namespace package) gives
it a real ``__spec__.origin`` so ``importlib.resources`` can locate the JSON
fixtures on every supported Python, including 3.9.
"""
