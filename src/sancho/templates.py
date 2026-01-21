"""
Template Manager Compatibility Layer

This module provides backward compatibility for code that imports
from src.sancho.templates. The actual implementation is in template_renderer.py.
"""

from src.sancho.template_renderer import TemplateRenderer, get_template_renderer

# Aliases for backward compatibility
TemplateManager = TemplateRenderer
get_template_manager = get_template_renderer

__all__ = ["TemplateManager", "get_template_manager"]
