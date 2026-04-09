# Scriptor API Documentation Configuration
# Build with: sphinx-apidoc -f -o source/ ../core ../tools ../hooks
#             sphinx-build -b html source/ build/

project = "Scriptor"
copyright = "2026, ysf7762-dev"
author = "ysf7762-dev"
version = "1.0"
release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "m2r2",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/__pycache__**"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "asyncio": ("https://docs.python.org/3/library/asyncio.html", None),
}

master_doc = "index"
