#!/usr/bin/env python
from jinja2 import Template
import os


index_template_str = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
  </head>
  <body>
    <ul>
    {%- for page in pages %}
      <li><a href="{{ page + ".html" }}">{{ page }}</a></li>
    {% endfor -%}
    </ul>
  </body>
</html>
"""

index_template = Template(index_template_str, autoescape=True)


def create_index(path):
    """Create an index page for the given directory.

    For each sub-directory, a link to that sub directory's index page will be
    used as the link target. For each normal file, a link to that file will be
    used.

    Returns a string of the index page.
    """
    pass
