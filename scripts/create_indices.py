#!/usr/bin/env python
from __future__ import print_function
from jinja2 import Template
import os
import sys


index_template_str = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
  </head>
  <body>
    <ul>
    {%- for page in pages %}
    <li><a href="{{ page }}">{{ page.rsplit('.', 1)[0] }}</a></li>
    {% endfor -%}
    </ul>
  </body>
</html>
"""

index_template = Template(index_template_str, autoescape=True)


def main(out_dir, filenames):
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        if not filenames[0].endswith('.html'):
            filenames = map(lambda f: os.path.join(f, 'index.html'), filenames)
        index_page = index_template.render(pages=filenames)
        f.write(index_page)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("More than two arguments required.\n"
              "Usage: {} out_directory linked_file1 [linked_fileN]".format(
                  sys.argv[0]))
        sys.exit(1)
    main(sys.argv[1], sys.argv[2:])
