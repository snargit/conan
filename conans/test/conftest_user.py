tools_locations = {
    'svn': {"disabled": True},
    'cmake': {
        "default": "3.25",
        "3.15": {"disabled": True},
        "3.16": {"disabled": True},
        "3.17": {"disabled": True},
        "3.19": {"disabled": True},
        # To explicitly skip one tool for one version, define the path as 'skip-tests'
        # if you don't define the path for one platform it will run the test with the
        # tool in the path. For example here it will skip the test with CMake in Darwin but
        # in Linux it will run with the version found in the path if it's not specified
        "3.23": {"disabled": True},
        "3.25": {"path": {"Darwin": "skip-tests"}},
    },
    'ninja': { "disabled": True},
    'meson': {"disabled": True},
    'bazel':  {"disabled": True}
}
