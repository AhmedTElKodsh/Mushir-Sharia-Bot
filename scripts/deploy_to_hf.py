#!/usr/bin/env python3
"""Compatibility wrapper for the governed Hugging Face Space deploy script."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    deploy_script = Path(__file__).with_name("deploy_huggingface_space.py")
    runpy.run_path(str(deploy_script), run_name="__main__")
