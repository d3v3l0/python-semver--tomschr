#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# python-semver documentation build configuration file
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import codecs
import os
import re
import sys

SRC_DIR = os.path.abspath("../src/")
sys.path.insert(0, SRC_DIR)
# from semver import __version__  # noqa: E402


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, *parts), "rb", "utf-8") as f:
        return f.read()


def find_version(*file_paths):
    """
    Build a path from *file_paths* and search for a ``__version__``
    string inside.
    """
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
]

# Autodoc configuration
autoclass_content = "class"
autodoc_typehints = "signature"
autodoc_member_order = "alphabetical"
add_function_parentheses = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "python-semver"
copyright = "2018, Kostiantyn Rybnikov and all"
author = "Kostiantyn Rybnikov and all"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
release = find_version("../src/semver/__about__.py")
# The full version, including alpha/beta/rc tags.
version = release  # .rsplit(u".", 1)[0]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# Markup to shorten external links
# See https://www.sphinx-doc.org/en/master/usage/extensions/extlinks.html
extlinks = {
    "gh": ("https://github.com/python-semver/python-semver/issues/%s", "#"),
    "pr": ("https://github.com/python-semver/python-semver/pull/%s", "PR #"),
}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"
templates_path = ["_templates"]

GITHUB_URL = "https://github.com/python-semver/python-semver"

html_theme_options = {
    # -- Basics
    #: Text blurb about your project to appear under the logo:
    # "description": "Semantic versioning",
    #: Makes the sidebar "fixed" or pinned in place:
    "fixed_sidebar": True,
    #: Relative path to $PROJECT/_static to logo image:
    "logo": "logo.svg",
    #: Set to true to insert your site's project name under
    #: the logo:
    # "logo_name": True,
    #: CSS width specifier controller default sidebar width:
    "sidebar_width": "25%",
    #: CSS width specifier controlling default content/page width:
    "page_width": "auto",
    #: CSS width specifier controlling default body text width:
    "body_max_width": "auto",
    #
    # -- Service Links and Badges
    #: Contains project name and user of GitHub:
    "github_user": "python-semver",
    "github_repo": "python-semver",
    #: whether to link to your GitHub:
    "github_button": True,
    #:
    "github_type": "star",
    #: whether to apply a ‘Fork me on Github’ banner
    #: in the top right corner of the page:
    # "github_banner": True,
    #
    # -- Non-service sidebar control
    #: Dictionary mapping link names to link targets:
    "extra_nav_links": {
        "PyPI": "https://pypi.org/project/semver/",
        "Libraries.io": "https://libraries.io/pypi/semver",
    },
    #: Boolean determining whether all TOC entries that
    #: are not ancestors of the current page are collapsed:
    "sidebar_collapse": True,
    #
    # -- Header/footer options
    #: used to display next and previous links above and
    #: below the main page content
    "show_relbars": True,
    "show_relbar_top": True,
    #
    # -- Style colors
    # "anchor": "",
    # "anchor_hover_bg": "",
    # "anchor_hover_fg": "",
    "narrow_sidebar_fg": "lightgray",
    #
    # -- Fonts
    # "code_font_size": "",
    "font_family": "'Roboto',sans-serif",
    "head_font_family": "'Roboto Slab',serif",
    "code_font_family": "'Roboto Mono',monospace",
    "font_size": "1.20rem",
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]

# html_logo = "logo.svg"

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "semverdoc"


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        "semver.tex",
        "python-semver Documentation",
        "Kostiantyn Rybnikov and all",
        "manual",
    )
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
manpage_doc = "pysemver"

man_pages = [
    (
        manpage_doc,
        "pysemver",
        "Helper script for Semantic Versioning",
        ["Thomas Schraitle"],
        1,
    )
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "semver",
        "python-semver Documentation",
        author,
        "semver",
        "One line description of project.",
        "Miscellaneous",
    )
]

# ----------------
# Setup for Sphinx


def remove_noqa(app, what, name, obj, options, lines):
    """Remove any 'noqa' parts in a docstring"""
    noqa_pattern = re.compile(r"\s+# noqa:.*$")
    # Remove any "# noqa" parts in a line
    for idx, line in enumerate(lines):
        lines[idx] = noqa_pattern.sub("", line, count=1)


def setup(app):
    """Set up the Sphinx app."""
    app.connect("autodoc-process-docstring", remove_noqa)
