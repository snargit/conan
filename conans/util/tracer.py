import copy
import os

from conan.api.output import ConanOutput
from conans.model.package_ref import PkgReference
from conans.model.recipe_ref import RecipeReference
from conans.util.files import md5sum, sha1sum


# FIXME: Conan 2.0 the traces should have all the revisions information also.


MASKED_FIELD = "**********"

# ############## LOG METHODS ######################


def _file_document(name, path):
    if os.path.isdir(path):
        return {"name": name, "path": path, "type": "folder"}
    else:
        return {"name": name, "path": path, "md5": md5sum(path),
                "sha1": sha1sum(path), "type": "folder"}


def log_recipe_sources_download(ref, duration, remote_name, files_downloaded):
    assert(isinstance(ref, RecipeReference))
    files_downloaded = files_downloaded or {}
    files_downloaded = [_file_document(name, path) for name, path in files_downloaded.items()]
    data = {"_action": "DOWNLOADED_RECIPE_SOURCES", "_id": repr(ref),
                                                    "duration": duration,
                                                    "remote": remote_name,
                                                    "files": files_downloaded}
    ConanOutput().trace(data)


def log_package_download(pref, duration, remote, files_downloaded):
    files_downloaded = files_downloaded or {}
    files_downloaded = [_file_document(name, path) for name, path in files_downloaded.items()]
    data = {"_action": "DOWNLOADED_PACKAGE", "_id": repr(pref), "duration": duration,
            "remote": remote.name, "files": files_downloaded}
    ConanOutput().trace(data)


def log_package_got_from_local_cache(pref):
    assert(isinstance(pref, PkgReference))
    tmp = copy.copy(pref)
    tmp.revision = None
    data = {"_action": "GOT_PACKAGE_FROM_LOCAL_CACHE", "_id": repr(tmp)}
    ConanOutput().trace(data)


def log_package_built(pref, duration, log_run=None):
    assert(isinstance(pref, PkgReference))
    tmp = copy.copy(pref)
    tmp.revision = None
    data = {"_action": "PACKAGE_BUILT_FROM_SOURCES", "_id": repr(tmp), "duration": duration,
            "log": log_run}
    ConanOutput().trace(data)


def log_client_rest_api_call(url, method, duration, headers):
    headers = copy.copy(headers)
    if "Authorization" in headers:
        headers["Authorization"] = MASKED_FIELD
    if "X-Client-Anonymous-Id" in headers:
        headers["X-Client-Anonymous-Id"] = MASKED_FIELD
    if "signature=" in url:
        url = url.split("signature=")[0] + "signature=%s" % MASKED_FIELD

    data = {"_action": "REST_API_CALL", "method": method, "url": url, "duration": duration,
            "headers": headers}
    ConanOutput().trace(data)


def log_download(url, duration):
    data = {"_action": "DOWNLOAD", "url": url, "duration": duration}
    ConanOutput().trace(data)


def log_uncompressed_file(src_path, duration, dest_folder):
    data = {"_action": "UNZIP", "src": src_path, "dst": dest_folder, "duration": duration}
    ConanOutput().trace(data)
