import re
import hashlib
from werkzeug.exceptions import NotFound
from flask import Flask, send_file, safe_join, url_for, g, current_app, abort


def get_file_hash(filename):
    if not hasattr(g, 'static_hashes'):
        g.static_hashes = {}
    # Check the cache if not in debug mode
    if not current_app.debug:
        try:
            return g.static_hashes[filename]
        except KeyError:
            pass
    hasher = hashlib.md5()
    with open(safe_join(current_app.static_folder, filename), 'rb') as f:
        hasher.update(f.read())
    filehash = hasher.hexdigest()[:8]
    g.static_hashes[filename] = filehash
    return filehash


def static_file(filename, **kwargs):
    if current_app.config['SRP_STATIC_FILE_HASH']:
        filehash = get_file_hash(filename)
        beginning, extension = filename.rsplit('.', 1)
        filename = '{}.{}.{}'.format(beginning, filehash, extension)
    return url_for('static', filename=filename, **kwargs)


class VersionedStaticFlask(Flask):

    def send_static_file(self, filename):
        # Short-circuit if not adding file hashes
        if not self.config['SRP_STATIC_FILE_HASH']:
            return super(VersionedStaticFlask, self).send_static_file(filename)
        try:
            return super(VersionedStaticFlask, self).send_static_file(filename)
        except NotFound as e:
            current_app.logger.debug(u"Checking for version-hashed file: {}".
                    format(filename))
            # Map file names are derived from the source file's name, so ignore
            # the '.map' at the end.
            if filename.endswith('.map'):
                hashed_filename = filename[:-4]
            else:
                hashed_filename = filename
            # Extract the file hash from the name
            filename_match = re.match(r'(.+)\.([0-9a-fA-F]{8})(\.\w+)$',
                    hashed_filename)
            if filename_match is None:
                current_app.logger.warning(u"Hash was unable to be found.")
                raise e
            requested_hash = filename_match.group(2)
            real_filename = filename_match.group(1) + filename_match.group(3)
            if filename != hashed_filename:
                real_filename += '.map'
            return super(VersionedStaticFlask, self).send_static_file(
                    real_filename)
