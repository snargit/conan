from conan.api.conan_api import ConanAPI
from conan.api.model import ListPattern
from conan.cli.command import conan_command, conan_subcommand, OnceArgument
from conan.cli.commands import default_text_formatter
from conans.errors import ConanException
from conans.model.package_ref import PkgReference
from conans.model.recipe_ref import RecipeReference


@conan_command(group="Consumer")
def cache(conan_api: ConanAPI, parser, *args):
    """Performs file operations in the local cache (of recipes and packages)
    """
    pass


@conan_subcommand(formatters={"text": default_text_formatter})
def cache_path(conan_api: ConanAPI, parser, subparser, *args):
    """
        Shows the path in the Conan cache af a given reference
    """
    subparser.add_argument("reference", help="Recipe reference or Package reference")
    subparser.add_argument("--folder", choices=['export_source', 'source', 'build'],
                           help="Show the path to the specified element. The 'build'"
                                " requires a package reference. If not specified it shows 'exports'"
                                " path ")

    args = parser.parse_args(*args)
    try:
        pref = PkgReference.loads(args.reference)
    except ConanException:
        pref = None

    if not pref:  # Not a package reference
        ref = RecipeReference.loads(args.reference)
        if args.folder is None:
            path = conan_api.cache.export_path(ref)
        elif args.folder == "export_source":
            path = conan_api.cache.export_source_path(ref)
        elif args.folder == "source":
            path = conan_api.cache.source_path(ref)
        else:
            raise ConanException(f"'--folder {args.folder}' requires a valid package reference")
    else:
        if args.folder is None:
            path = conan_api.cache.package_path(pref)
        elif args.folder == "build":
            path = conan_api.cache.build_path(pref)
        else:
            raise ConanException(f"'--folder {args.folder}' requires a recipe reference")
    return path


@conan_subcommand()
def cache_clean(conan_api: ConanAPI, parser, subparser, *args):
    """
        Shows the path in the Conan cache af a given reference
    """
    subparser.add_argument("pattern", help="selection pattern for references to clean")
    subparser.add_argument("-s", "--source", action='store_true', default=False,
                           help="Clean source folders")
    subparser.add_argument("-b", "--build", action='store_true', default=False,
                           help="Clean source folders")
    subparser.add_argument("-d", "--download", action='store_true', default=False,
                           help="Clean download folders")
    subparser.add_argument('-p', '--package-query', action=OnceArgument,
                           help="Remove all packages (empty) or provide a query: "
                                "os=Windows AND (arch=x86 OR compiler=gcc)")
    args = parser.parse_args(*args)

    if not args.source and not args.build and not args.download:
        raise ConanException("Define at least one argument from --source, --build, --download")

    ref_pattern = ListPattern(args.pattern, rrev="*", package_id="*", prev="*")
    package_list = conan_api.list.select(ref_pattern, package_query=args.package_query)
    conan_api.cache.clean(package_list, source=args.source, build=args.build,
                          download=args.download)
