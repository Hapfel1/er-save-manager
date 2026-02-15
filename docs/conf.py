# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------

project = 'Elden Ring Save Manager'
copyright = '2026, Hapfel'
author = 'Hapfel'
release = '0.10.1'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'myst_parser',  # Markdown support
]

# Add markdown support
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
    'style_nav_header_background': '#1e1e2e',  # Catppuccin base
}

# Custom CSS
html_css_files = [
    'custom.css',
]


# Show "Edit on GitHub" links
html_context = {
    'display_github': True,
    'github_user': 'Hapfel',
    'github_repo': 'er-save-manager',
    'github_version': 'main',
    'conf_py_path': '/docs/',
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '11pt',  # Slightly larger for print
}

latex_documents = [
    ('index', 'EldenRingSaveManager.tex', 'Elden Ring Save Manager Documentation',
     'Hapfel', 'manual'),
]

# -- Extension configuration -------------------------------------------------

# Napoleon settings for Google/NumPy docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# MyST (Markdown) parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "tasklist",
]

myst_heading_anchors = 3

# Suppress warnings
suppress_warnings = ['myst.header']