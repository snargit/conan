import os
import textwrap
import time
import unittest

import pytest
from parameterized import parameterized

from conans.model.recipe_ref import RecipeReference
from conans.paths import CONANFILE
from conans.test.utils.tools import TestClient, GenConanfile


class PyRequiresExtendTest(unittest.TestCase):

    @staticmethod
    def _define_base(client):
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                def source(self):
                    self.output.info("My cool source!")
                def build(self):
                    self.output.info("My cool build!")
                def package(self):
                    self.output.info("My cool package!")
                def package_info(self):
                    self.output.info("My cool package_info!")
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")

    def test_reuse(self):
        client = TestClient(default_server_user=True)
        self._define_base(client)
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
            """)
        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        package_id = client.created_package_id("pkg/0.1@user/testing")
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)

        client.run("upload * --confirm -r default")
        client.run("remove * -c")
        client.run("install --requires=pkg/0.1@user/testing")
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)
        client.run("remove * -c")
        client.run("download pkg/0.1@user/testing#latest:* -r default")
        self.assertIn(f"pkg/0.1@user/testing: Package installed {package_id}", client.out)

    def test_reuse_dot(self):
        client = TestClient(default_server_user=True)
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                def build(self):
                    self.output.info("My cool build!")
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=my.base --version=1.1 --user=user --channel=testing")
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "my.base/1.1@user/testing"
                python_requires_extend = "my.base.MyConanfileBase"
            """)
        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)

    @pytest.mark.xfail(reason="Lockfiles with alias are broken, never were tested")
    def test_with_alias(self):
        client = TestClient()
        self._define_base(client)
        client.alias("base/latest@user/testing",  "base/1.1@user/testing")

        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/(latest)@user/testing"
                python_requires_extend = "base.MyConanfileBase"
            """)
        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)

    def test_reuse_version_ranges(self):
        client = TestClient()
        self._define_base(client)

        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/[>1.0,<1.2]@user/testing"
                python_requires_extend = "base.MyConanfileBase"
            """)

        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        client.assert_listed_require({"base/1.1@user/testing": "Cache"}, python=True)
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)

    def test_multiple_reuse(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class SourceBuild(ConanFile):
                def source(self):
                    self.output.info("My cool source!")
                def build(self):
                    self.output.info("My cool build!")
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=sourcebuild --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class PackageInfo(ConanFile):
                def package(self):
                    self.output.info("My cool package!")
                def package_info(self):
                    self.output.info("My cool package_info!")
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=packageinfo --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                python_requires = "sourcebuild/1.0@user/channel", "packageinfo/1.0@user/channel"
                python_requires_extend = "sourcebuild.SourceBuild", "packageinfo.PackageInfo"
            """)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)

    @staticmethod
    def test_transitive_access():
        client = TestClient()
        client.save({"conanfile.py": GenConanfile()})
        client.run("export . --name=base --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class Helper(ConanFile):
                python_requires = "base/1.0@user/channel"
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=helper --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                python_requires = "helper/1.0@user/channel"
                def build(self):
                    self.python_requires["base"]
            """)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=channel")
        assert "pkg/0.1@user/channel: Created package" in client.out

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class Pkg(ConanFile):
                python_requires = "helper/1.0@user/channel"
                python_requires_extend = "base.HelloConan"
            """)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=channel")
        assert "pkg/0.1@user/channel: Created package" in client.out

    def test_multiple_requires_error(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            myvar = 123
            def myfunct():
                return 123
            class Pkg(ConanFile):
                pass
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=pkg1 --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            myvar = 234
            def myfunct():
                return 234
            class Pkg(ConanFile):
                pass
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=pkg2 --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                python_requires = "pkg1/1.0@user/channel", "pkg2/1.0@user/channel"
                def build(self):
                    self.output.info("PKG1 N: %s" % self.python_requires["pkg1"].conanfile.name)\
                               .info("PKG1 V: %s" % self.python_requires["pkg1"].conanfile.version)\
                               .info("PKG1 U: %s" % self.python_requires["pkg1"].conanfile.user)\
                               .info("PKG1 C: %s" % self.python_requires["pkg1"].conanfile.channel)\
                               .info("PKG1 : %s" % self.python_requires["pkg1"].module.myvar)\
                               .info("PKG2 : %s" % self.python_requires["pkg2"].module.myvar)\
                               .info("PKG1F : %s" % self.python_requires["pkg1"].module.myfunct())\
                               .info("PKG2F : %s" % self.python_requires["pkg2"].module.myfunct())
            """)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=consumer --version=0.1 --user=user --channel=testing")
        self.assertIn("consumer/0.1@user/testing: PKG1 N: pkg1", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG1 V: 1.0", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG1 U: user", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG1 C: channel", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG1 : 123", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG2 : 234", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG1F : 123", client.out)
        self.assertIn("consumer/0.1@user/testing: PKG2F : 234", client.out)

    def test_local_import(self):
        client = TestClient(default_server_user=True)
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            import mydata
            class MyConanfileBase(ConanFile):
                exports = "*.py"
                def source(self):
                    self.output.info(mydata.src)
                def build(self):
                    self.output.info(mydata.build)
                def package(self):
                    self.output.info(mydata.pkg)
                def package_info(self):
                    self.output.info(mydata.info)
            """)
        mydata = textwrap.dedent("""
            src = "My cool source!"
            build = "My cool build!"
            pkg = "My cool package!"
            info = "My cool package_info!"
            """)
        client.save({"conanfile.py": conanfile,
                     "mydata.py": mydata})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
            """)

        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        package_id = client.created_package_id("pkg/0.1@user/testing")
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)

        client.run("upload * --confirm -r default")
        client.run("remove * -c")
        client.run("install --requires=pkg/0.1@user/testing")
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)
        client.run("remove * -c")
        client.run("download pkg/0.1@user/testing#*:* -r default")
        self.assertIn(f"pkg/0.1@user/testing: Package installed {package_id}", client.out)

    def test_reuse_class_members(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                license = "MyLicense"
                author = "author@company.com"
                exports = "*.txt"
                exports_sources = "*.h"
                short_paths = True
                generators = "CMakeToolchain"
            """)
        client.save({"conanfile.py": conanfile,
                     "header.h": "some content"})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")

        reuse = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            import os
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
                def build(self):
                    self.output.info("Exports sources! %s" % self.exports_sources)
                    self.output.info("HEADER CONTENT!: %s" % load(self, "header.h"))
                    self.output.info("Short paths! %s" % self.short_paths)
                    self.output.info("License! %s" % self.license)
                    self.output.info("Author! %s" % self.author)
                    assert os.path.exists("conan_toolchain.cmake")
            """)
        client.save({"conanfile.py": reuse,
                     "header.h": "pkg new header contents",
                     "other.txt": "text"})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: Exports sources! *.h", client.out)
        self.assertIn("pkg/0.1@user/testing exports: Copied 1 '.txt' file: other.txt",
                      client.out)
        self.assertIn("pkg/0.1@user/testing exports_sources: Copied 1 '.h' file: header.h",
                      client.out)
        self.assertIn("pkg/0.1@user/testing: Short paths! True", client.out)
        self.assertIn("pkg/0.1@user/testing: License! MyLicense", client.out)
        self.assertIn("pkg/0.1@user/testing: Author! author@company.com", client.out)
        self.assertIn("pkg/0.1@user/testing: HEADER CONTENT!: pkg new header contents", client.out)
        ref = RecipeReference.loads("pkg/0.1@user/testing")
        self.assertTrue(os.path.exists(os.path.join(client.get_latest_ref_layout(ref).export(),
                                                    "other.txt")))

    def test_reuse_system_requirements(self):
        # https://github.com/conan-io/conan/issues/7718
        client = TestClient()
        conanfile = textwrap.dedent("""
           from conan import ConanFile
           class MyConanfileBase(ConanFile):
               def system_requirements(self):
                   self.output.info("My system_requirements %s being called!" % self.name)
           """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
            """)
        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: My system_requirements pkg being called!", client.out)

    def test_overwrite_class_members(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                license = "MyLicense"
                author = "author@company.com"
                settings = "os", # tuple!
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")

        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                license = "MIT"
                author = "frodo"
                settings = "arch", # tuple!
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"

                def init(self):
                    base = self.python_requires["base"].module.MyConanfileBase
                    self.settings = base.settings + self.settings
                    self.license = base.license

                def build(self):
                    self.output.info("License! %s" % self.license)
                    self.output.info("Author! %s" % self.author)
                    self.output.info("os: %s arch: %s" % (self.settings.get_safe("os"),
                                                          self.settings.arch))
            """)
        client.save({"conanfile.py": reuse})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing -s os=Windows -s arch=armv7")
        self.assertIn("pkg/0.1@user/testing: License! MyLicense", client.out)
        self.assertIn("pkg/0.1@user/testing: Author! frodo", client.out)
        self.assertIn("pkg/0.1@user/testing: os: Windows arch: armv7", client.out)

    def test_failure_init_method(self):
        client = TestClient()
        base = textwrap.dedent("""
            from conan import ConanFile
            class MyBase(object):
                settings = "os", "build_type", "arch"
                options = {"base_option": [True, False]}
                default_options = {"base_option": False}

            class BaseConanFile(ConanFile):
                pass
            """)
        client.save({"conanfile.py": base})
        client.run("export . --name=base --version=1.0")
        derived = textwrap.dedent("""
            from conan import ConanFile
            class DerivedConan(ConanFile):
                settings = "os", "build_type", "arch"

                python_requires = "base/1.0"
                python_requires_extend = 'base.MyBase'

                options = {"derived_option": [True, False]}
                default_options = {"derived_option": False}

                def init(self):
                    base = self.python_requires['base'].module.MyBase
                    self.options.update(base.options, base.default_options)
                """)
        client.save({"conanfile.py": derived})
        client.run("create . --name=pkg --version=0.1 -o base_option=True -o derived_option=True")
        self.assertIn("pkg/0.1: Created package", client.out)
        client.run("create . --name=pkg --version=0.1 -o whatever=True", assert_error=True)
        assert "Possible options are ['derived_option', 'base_option']" in client.out

    def test_transitive_imports_conflicts(self):
        # https://github.com/conan-io/conan/issues/3874
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            import myhelper
            class SourceBuild(ConanFile):
                exports = "*.py"
            """)
        helper = textwrap.dedent("""
            def myhelp(output):
                output.info("MyHelperOutput!")
            """)
        client.save({"conanfile.py": conanfile,
                     "myhelper.py": helper})
        client.run("export . --name=base1 --version=1.0 --user=user --channel=channel")
        client.save({"myhelper.py": helper.replace("MyHelperOutput!", "MyOtherHelperOutput!")})
        client.run("export . --name=base2 --version=1.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile

            class MyConanfileBase(ConanFile):
                python_requires = "base2/1.0@user/channel", "base1/1.0@user/channel"
                def build(self):
                    self.python_requires["base1"].module.myhelper.myhelp(self.output)
                    self.python_requires["base2"].module.myhelper.myhelp(self.output)
            """)
        # This should work, even if there is a local "myhelper.py" file, which could be
        # accidentaly imported (and it was, it was a bug)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: MyHelperOutput!", client.out)
        self.assertIn("pkg/0.1@user/testing: MyOtherHelperOutput!", client.out)

        # Now, the same, but with "clean_first=True", should keep working
        client.save({"conanfile.py": conanfile}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: MyHelperOutput!", client.out)
        self.assertIn("pkg/0.1@user/testing: MyOtherHelperOutput!", client.out)

    def test_update(self):
        client = TestClient(default_server_user=True)
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            somevar = 42
            class MyConanfileBase(ConanFile):
                pass
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")
        client.run("upload * --confirm -r default")

        client2 = TestClient(servers=client.servers, inputs=["user", "password"])
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
                def configure(self):
                    self.output.info("PYTHON REQUIRE VAR %s"
                                     % self.python_requires["base"].module.somevar)
        """)

        client2.save({"conanfile.py": reuse})
        client2.run("install .")
        self.assertIn("conanfile.py: PYTHON REQUIRE VAR 42", client2.out)

        client.save({"conanfile.py": conanfile.replace("42", "143")})
        time.sleep(1)  # guarantee time offset
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")
        client.run("upload * --confirm -r default")

        client2.run("install . --update")
        self.assertIn("conanfile.py: PYTHON REQUIRE VAR 143", client2.out)

    def test_update_ranges(self):
        # Same as the above, but using a version range, and no --update
        # https://github.com/conan-io/conan/issues/4650#issuecomment-497464305
        client = TestClient(default_server_user=True)
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            somevar = 42
            class MyConanfileBase(ConanFile):
                pass
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=base --version=1.1 --user=user --channel=testing")
        client.run("upload * --confirm -r default")

        client2 = TestClient(servers=client.servers, inputs=["user", "password"])
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/[>1.0]@user/testing"
                python_requires_extend = "base.MyConanfileBase"
                def configure(self):
                    self.output.info("PYTHON REQUIRE VAR %s"
                                     % self.python_requires["base"].module.somevar)
        """)

        client2.save({"conanfile.py": reuse})
        client2.run("install .")
        self.assertIn("conanfile.py: PYTHON REQUIRE VAR 42", client2.out)

        client.save({"conanfile.py": conanfile.replace("42", "143")})
        # Make sure to bump the version!
        client.run("export . --name=base --version=1.2 --user=user --channel=testing")
        client.run("upload * --confirm -r default")

        client2.run("install . --update")
        self.assertIn("conanfile.py: PYTHON REQUIRE VAR 143", client2.out)

    def test_duplicate_pyreq(self):
        t = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class PyReq(ConanFile):
                pass
        """)
        t.save({"conanfile.py": conanfile})
        t.run("export . --name=pyreq --version=1.0 --user=user --channel=channel")
        t.run("export . --name=pyreq --version=2.0 --user=user --channel=channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class Lib(ConanFile):
                python_requires = "pyreq/1.0@user/channel", "pyreq/2.0@user/channel"
        """)
        t.save({"conanfile.py": conanfile})
        t.run("create . --name=name --version=version --user=user --channel=channel", assert_error=True)
        self.assertIn("ERROR: Error loading conanfile", t.out)
        self.assertIn("The python_require 'pyreq' already exists", t.out)

    def test_local_build(self):
        client = TestClient()
        client.save({"conanfile.py": "var=42\n"+str(GenConanfile())})
        client.run("export . --name=tool --version=0.1 --user=user --channel=channel")
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                python_requires = "tool/0.1@user/channel"
                def source(self):
                    self.output.info("Pkg1 source: %s" % self.python_requires["tool"].module.var)
                def build(self):
                    self.output.info("Pkg1 build: %s" % self.python_requires["tool"].module.var)
                def package(self):
                    self.output.info("Pkg1 package: %s" % self.python_requires["tool"].module.var)
            """)
        client.save({"conanfile.py": conanfile})
        client.run("source .")
        self.assertIn("conanfile.py: Pkg1 source: 42", client.out)
        client.run("install .")
        client.run("build .")
        self.assertIn("conanfile.py: Pkg1 build: 42", client.out)
        client.run("export-pkg . --name=pkg1 --version=0.1 --user=user --channel=testing")

    def test_reuse_name_version(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            import os

            class Source(object):
                def set_name(self):
                    self.name = load(self, "name.txt")

                def set_version(self):
                    self.version = load(self, "version.txt")

            class MyConanfileBase(ConanFile):
                pass
            """)
        client.save({"conanfile.py": conanfile})
        client.run("export . --name=tool --version=0.1 --user=user --channel=channel")
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                python_requires = "tool/0.1@user/channel"
                python_requires_extend = "tool.Source"
                def source(self):
                    self.output.info("Pkg1 source: %s:%s" % (self.name, self.version))
                def build(self):
                    self.output.info("Pkg1 build: %s:%s" % (self.name, self.version))
                def package(self):
                    self.output.info("Pkg1 package: %s:%s" % (self.name, self.version))
            """)
        client.save({"conanfile.py": conanfile,
                     "name.txt": "mypkg",
                     "version.txt": "myversion"})
        client.run("export .")
        self.assertIn("mypkg/myversion: A new conanfile.py version was exported", client.out)
        client.run("create .")
        self.assertIn("mypkg/myversion: Pkg1 source: mypkg:myversion", client.out)
        self.assertIn("mypkg/myversion: Pkg1 build: mypkg:myversion", client.out)
        self.assertIn("mypkg/myversion: Pkg1 package: mypkg:myversion", client.out)

    @parameterized.expand([(False, False), (True, False), (True, True), ])
    def test_python_requires_with_alias(self, use_alias, use_alias_of_alias):
        assert use_alias if use_alias_of_alias else True
        version_str = "latest2" if use_alias_of_alias else "latest" if use_alias else "1.0"
        client = TestClient()

        # Create python_requires
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class PythonRequires0(ConanFile):
                def build(self):
                    self.output.info("PythonRequires0::build")
                    """)})
        client.run("export . --name=python_requires0 --version=1.0 --user=user --channel=test")
        client.alias("python_requires0/latest@user/test",  "python_requires0/1.0@user/test")
        client.alias("python_requires0/latest2@user/test",  "python_requires0/latest@user/test")

        # Create python requires, that require the previous one
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class PythonRequires1(ConanFile):
                python_requires = "python_requires0/{v}@user/test"
                python_requires_extend = "python_requires0.PythonRequires0"
                def build(self):
                    super(PythonRequires1, self).build()
                    self.output.info("PythonRequires1::build")
            """).format(v=version_str)})
        client.run("export . --name=python_requires1 --version=1.0 --user=user --channel=test")
        client.alias("python_requires1/latest@user/test",  "python_requires1/1.0@user/test")
        client.alias("python_requires1/latest2@user/test",  "python_requires1/latest@user/test")

        # Create python requires
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class PythonRequires11(ConanFile):
                def build(self):
                    super(PythonRequires11, self).build()
                    self.output.info("PythonRequires11::build")
                    """)})
        client.run("export . --name=python_requires11 --version=1.0 --user=user --channel=test")
        client.alias("python_requires11/latest@user/test",  "python_requires11/1.0@user/test")
        client.alias("python_requires11/latest2@user/test",  "python_requires11/latest@user/test")

        # Create python requires, that require the previous one
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class PythonRequires22(ConanFile):
                python_requires = "python_requires0/{v}@user/test"
                python_requires_extend = "python_requires0.PythonRequires0"
                def build(self):
                    super(PythonRequires22, self).build()
                    self.output.info("PythonRequires22::build")
                    """).format(v=version_str)})
        client.run("export . --name=python_requires22 --version=1.0 --user=user --channel=test")
        client.alias("python_requires22/latest@user/test",  "python_requires22/1.0@user/test")
        client.alias("python_requires22/latest2@user/test",  "python_requires22/latest@user/test")

        # Another python_requires, that requires the previous python requires
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class PythonRequires2(ConanFile):
                python_requires = "python_requires1/{v}@user/test", "python_requires11/{v}@user/test"
                python_requires_extend = ("python_requires1.PythonRequires1",
                                      "python_requires11.PythonRequires11")
                def build(self):
                    super(PythonRequires2, self).build()
                    self.output.info("PythonRequires2::build")
                    """).format(v=version_str)})
        client.run("export . --name=python_requires2 --version=1.0 --user=user --channel=test")
        client.alias("python_requires2/latest@user/test",  "python_requires2/1.0@user/test")
        client.alias("python_requires2/latest2@user/test",  "python_requires2/latest@user/test")

        # My project, will consume the latest python requires
        client.save({CONANFILE: textwrap.dedent("""
            from conan import ConanFile
            class Project(ConanFile):
                python_requires = "python_requires2/{v}@user/test", "python_requires22/{v}@user/test"
                python_requires_extend = ("python_requires2.PythonRequires2",
                                          "python_requires22.PythonRequires22")
                def build(self):
                    super(Project, self).build()
                    self.output.info("Project::build")
                    """).format(v=version_str)})

        client.run("create . --name=project --version=1.0 --user=user --channel=test --build=missing")

        # Check that everything is being built
        self.assertIn("project/1.0@user/test: PythonRequires11::build", client.out)
        self.assertIn("project/1.0@user/test: PythonRequires0::build", client.out)
        self.assertIn("project/1.0@user/test: PythonRequires22::build", client.out)
        self.assertIn("project/1.0@user/test: PythonRequires1::build", client.out)
        self.assertIn("project/1.0@user/test: PythonRequires2::build", client.out)
        self.assertIn("project/1.0@user/test: Project::build", client.out)

        # Check that all the graph is printed properly
        #   - requirements
        client.assert_listed_require({"project/1.0@user/test": "Cache"})
        #   - python requires
        client.assert_listed_require({"python_requires11/1.0@user/test": "Cache",
                                      "python_requires0/1.0@user/test": "Cache",
                                      "python_requires22/1.0@user/test": "Cache",
                                      "python_requires1/1.0@user/test": "Cache",
                                      "python_requires2/1.0@user/test": "Cache"}, python=True)
        #   - packages
        client.assert_listed_binary({"project/1.0@user/test":
                                     ("257a966344bb19ae8ef0c208eff085952902e25f", "Build")})

        #   - no mention to alias
        self.assertNotIn("alias", client.out)
        self.assertNotIn("alias2", client.out)

    def test_reuse_export_sources(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                exports = "*"
            """)
        client.save({"conanfile.py": conanfile,
                     "file.h": "myheader",
                     "folder/other.h": "otherheader"})
        client.run("export . --name=tool --version=0.1 --user=user --channel=channel")
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            import os
            class MyConanfileBase(ConanFile):
                python_requires = "tool/0.1@user/channel"
                def source(self):
                    sources = self.python_requires["tool"].path
                    file_h = os.path.join(sources, "file.h")
                    other_h = os.path.join(sources, "folder/other.h")
                    self.output.info("Source: tool header: %s" % load(self, file_h))
                    self.output.info("Source: tool other: %s" % load(self, other_h))
                def build(self):
                    sources = self.python_requires["tool"].path
                    file_h = os.path.join(sources, "file.h")
                    other_h = os.path.join(sources, "folder/other.h")
                    self.output.info("Build: tool header: %s" % load(self, file_h))
                    self.output.info("Build: tool other: %s" % load(self, other_h))
                def package(self):
                    sources = self.python_requires["tool"].path
                    file_h = os.path.join(sources, "file.h")
                    other_h = os.path.join(sources, "folder/other.h")
                    self.output.info("Package: tool header: %s" % load(self, file_h))
                    self.output.info("Package: tool other: %s" % load(self, other_h))
            """)
        client.save({"conanfile.py": conanfile,
                     "name.txt": "MyPkg",
                     "version.txt": "MyVersion"})
        client.run("export . --name=pkg --version=1.0 --user=user --channel=channel")
        self.assertIn("pkg/1.0@user/channel: A new conanfile.py version was exported", client.out)
        client.run("create . --name=pkg --version=1.0 --user=user --channel=channel")
        self.assertIn("pkg/1.0@user/channel: Source: tool header: myheader", client.out)
        self.assertIn("pkg/1.0@user/channel: Source: tool other: otherheader", client.out)
        self.assertIn("pkg/1.0@user/channel: Build: tool header: myheader", client.out)
        self.assertIn("pkg/1.0@user/channel: Build: tool other: otherheader", client.out)
        self.assertIn("pkg/1.0@user/channel: Package: tool header: myheader", client.out)
        self.assertIn("pkg/1.0@user/channel: Package: tool other: otherheader", client.out)

        # The local flow
        client.run("install .")
        client.run("source .")
        self.assertIn("conanfile.py: Source: tool header: myheader", client.out)
        self.assertIn("conanfile.py: Source: tool other: otherheader", client.out)
        client.run("build .")
        self.assertIn("conanfile.py: Build: tool header: myheader", client.out)
        self.assertIn("conanfile.py: Build: tool other: otherheader", client.out)

    @pytest.mark.xfail(reason="cache2.0 editables not considered yet")
    def test_reuse_exports(self):
        client = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            class MyConanfileBase(ConanFile):
                exports = "*"
            """)
        client.save({"conanfile.py": conanfile,
                     "file.h": "myheader",
                     "folder/other.h": "otherheader"})
        client.run("editable add . tool/0.1@user/channel")

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import load
            import os
            class MyConanfileBase(ConanFile):
                python_requires = "tool/0.1@user/channel"
                def source(self):
                    sources = self.python_requires["tool"].path
                    file_h = os.path.join(sources, "file.h")
                    other_h = os.path.join(sources, "folder/other.h")
                    self.output.info("Source: tool header: %s" % load(self, file_h))
                    self.output.info("Source: tool other: %s" % load(self, other_h))
                def build(self):
                    sources = self.python_requires["tool"].path
                    file_h = os.path.join(sources, "file.h")
                    other_h = os.path.join(sources, "folder/other.h")
                    self.output.info("Build: tool header: %s" % load(self, file_h))
                    self.output.info("Build: tool other: %s" % load(self, other_h))
            """)

        client2 = TestClient(cache_folder=client.cache_folder)
        client2.save({"conanfile.py": conanfile,
                      "name.txt": "MyPkg",
                      "version.txt": "MyVersion"})

        # The local flow
        client2.run("install .")
        client2.run("source .")
        self.assertIn("conanfile.py: Source: tool header: myheader", client2.out)
        self.assertIn("conanfile.py: Source: tool other: otherheader", client2.out)
        client2.run("build .")
        self.assertIn("conanfile.py: Build: tool header: myheader", client2.out)
        self.assertIn("conanfile.py: Build: tool other: otherheader", client2.out)

    def test_build_id(self):
        client = TestClient(default_server_user=True)
        self._define_base(client)
        reuse = textwrap.dedent("""
            from conan import ConanFile
            class PkgTest(ConanFile):
                python_requires = "base/1.1@user/testing"
                python_requires_extend = "base.MyConanfileBase"
                def build_id(self):
                    pass
            """)
        client.save({"conanfile.py": reuse}, clean_first=True)
        client.run("create . --name=pkg --version=0.1 --user=user --channel=testing")
        self.assertIn("pkg/0.1@user/testing: My cool source!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool build!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package!", client.out)
        self.assertIn("pkg/0.1@user/testing: My cool package_info!", client.out)


def test_transitive_python_requires():
    # https://github.com/conan-io/conan/issues/8546
    client = TestClient()
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        myvar = 123
        def myfunct():
            return 234
        class SharedFunction(ConanFile):
            name = "shared-function"
            version = "1.0"
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class BaseClass(ConanFile):
            name = "base-class"
            version = "1.0"
            python_requires = "shared-function/1.0@user/channel"
            def build(self):
                pyreqs = self.python_requires
                v = pyreqs["shared-function"].module.myvar  # v will be 123
                f = pyreqs["shared-function"].module.myfunct()  # f will be 234
                self.output.info("%s, %s" % (v, f))
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class Consumer(ConanFile):
            name = "consumer"
            version = "1.0"
            python_requires = "base-class/1.0@user/channel"
            python_requires_extend = "base-class.BaseClass"
        """)
    client.save({"conanfile.py": conanfile})
    client.run("create . --user=user --channel=channel")
    assert "consumer/1.0@user/channel: Calling build()\nconsumer/1.0@user/channel: 123, 234" in \
           client.out


def test_transitive_diamond_python_requires():
    client = TestClient()
    conanfile = textwrap.dedent("""
        from conan import ConanFile
        myvar = 123
        def myfunct():
            return 234
        class SharedFunction(ConanFile):
            name = "shared-function"
            version = "1.0"
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        myvar = 222
        def myfunct():
            return 2222
        class SharedFunction2(ConanFile):
            name = "shared-function2"
            version = "1.0"
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class BaseClass(ConanFile):
            name = "base-class"
            version = "1.0"
            python_requires = "shared-function/1.0@user/channel", "shared-function2/1.0@user/channel"
            def build(self):
                pyreqs = self.python_requires
                v = pyreqs["shared-function"].module.myvar  # v will be 123
                f = pyreqs["shared-function2"].module.myfunct()  # f will be 2222
                self.output.info("%s, %s" % (v, f))
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class BaseClass2(ConanFile):
            name = "base-class2"
            version = "1.0"
            python_requires = "shared-function/1.0@user/channel", "shared-function2/1.0@user/channel"
            def package(self):
                pyreqs = self.python_requires
                v = pyreqs["shared-function2"].module.myvar  # v will be 222
                f = pyreqs["shared-function"].module.myfunct()  # f will be 234
                self.output.info("%s, %s" % (v, f))
        """)
    client.save({"conanfile.py": conanfile})
    client.run("export . --user=user --channel=channel")

    conanfile = textwrap.dedent("""
        from conan import ConanFile
        class Consumer(ConanFile):
            name = "consumer"
            version = "1.0"
            python_requires = "base-class/1.0@user/channel", "base-class2/1.0@user/channel"
            python_requires_extend = "base-class.BaseClass", "base-class2.BaseClass2"
        """)
    client.save({"conanfile.py": conanfile})
    client.run("create . --user=user --channel=channel")
    assert "consumer/1.0@user/channel: Calling build()\nconsumer/1.0@user/channel: 123, 2222" in \
           client.out
    assert "consumer/1.0@user/channel: Calling package()\nconsumer/1.0@user/channel: 222, 234" in \
           client.out


def test_multiple_reuse():
    """ test how to enable the multiple code reuse for custom user generators
        # https://github.com/conan-io/conan/issues/11589
    """

    c = TestClient()
    common = textwrap.dedent("""
        from conan import ConanFile
        def mycommon():
            return 42
        class Common(ConanFile):
            name = "common"
            version = "0.1"
        """)
    tool = textwrap.dedent("""
        from conan import ConanFile

        class MyGenerator:
            common = None
            def __init__(self, conanfile):
                self.conanfile = conanfile
            def generate(self):
                self.conanfile.output.info("VALUE TOOL: {}!!!".format(MyGenerator.common.mycommon()))

        class Tool(ConanFile):
            name = "tool"
            version = "0.1"
            python_requires = "common/0.1"
            def init(self):
                MyGenerator.common = self.python_requires["common"].module
        """)
    consumer = textwrap.dedent("""
        from conan import ConanFile
        class Consumer(ConanFile):
            python_requires = "tool/0.1", "common/0.1"
            def generate(self):
                mycommon = self.python_requires["common"].module.mycommon
                self.output.info("VALUE COMMON: {}!!!".format(mycommon()))
                mygenerator = self.python_requires["tool"].module.MyGenerator(self)
                mygenerator.generate()
        """)
    c.save({"common/conanfile.py": common,
            "tool/conanfile.py": tool,
            "consumer/conanfile.py": consumer})
    c.run("export common")
    c.run("export tool")
    c.run("install consumer")
    assert "VALUE COMMON: 42!!!" in c.out
    assert "VALUE TOOL: 42!!!" in c.out


class TestTestPackagePythonRequire:
    def test_test_package_python_requires(self):
        """ test how to test_package a python_require
        """

        c = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            def mycommon():
                return 42
            class Common(ConanFile):
                name = "common"
                version = "0.1"
                package_type = "python-require"
            """)
        test = textwrap.dedent("""
            from conan import ConanFile

            class Tool(ConanFile):
                def test(self):
                    self.output.info("{}!!!".format(self.python_requires["common"].module.mycommon()))
            """)
        c.save({"conanfile.py": conanfile,
                "test_package/conanfile.py": test})
        c.run("create .")
        assert "common/0.1 (test package): 42!!!" in c.out

    def test_test_package_python_requires_configs(self):
        """ test how to test_package a python_require with various configurations
        """

        c = TestClient()
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            def mycommon(build_type):
                return str(build_type).upper() + "OK"
            class Common(ConanFile):
                name = "common"
                version = "0.1"
                package_type = "python-require"
            """)
        test = textwrap.dedent("""
            from conan import ConanFile

            class Tool(ConanFile):
                settings = "build_type"
                def test(self):
                    result = self.python_requires["common"].module.mycommon(self.settings.build_type)
                    self.output.info("{}!!!".format(result))
            """)
        c.save({"conanfile.py": conanfile,
                "test_package/conanfile.py": test})
        c.run("create . ")
        assert "common/0.1 (test package): RELEASEOK!!!" in c.out
        c.run("create . -s build_type=Debug")
        assert "common/0.1 (test package): DEBUGOK!!!" in c.out


class TestResolveRemote:
    def test_resolve_remote_export(self):
        """ a "conan export" command should work even when a python_requires
        is in the server
        """
        c = TestClient(default_server_user=True)
        c.save({"common/conanfile.py": GenConanfile("tool", "0.1"),
                "pkg/conanfile.py": GenConanfile("pkg", "0.1").with_python_requires("tool/0.1")})
        c.run("export common")
        c.run("upload * -r=default -c")
        c.run("remove * -c")
        c.run("create pkg")
        assert "tool/0.1: Downloaded recipe" in c.out

        c.run("remove * -c")
        c.run("export pkg")
        assert "tool/0.1: Downloaded recipe" in c.out

        c.run("remove * -c")
        c.run("export pkg -r=default")
        assert "tool/0.1: Downloaded recipe" in c.out

        c.run("remove * -c")
        c.run("create pkg -r=default")
        assert "tool/0.1: Downloaded recipe" in c.out

    def test_missing_python_require_error(self):
        """ make sure the error is clear enough for users UX
        """
        c = TestClient()
        c.save({"pkg/conanfile.py": GenConanfile("pkg", "0.1").with_python_requires("tool/0.1")})
        c.run("create pkg", assert_error=True)
        assert "Cannot resolve python_requires 'tool/0.1'" in c.out


class TestTransitiveExtend:
    # https://github.com/conan-io/conan/issues/10511
    # https://github.com/conan-io/conan/issues/10565
    def test_transitive_extend(self):
        client = TestClient()
        company = textwrap.dedent("""
            from conan import ConanFile
            class CompanyConanFile(ConanFile):
                name = "company"
                version = "1.0"

                def msg1(self):
                    return "company"
                def msg2(self):
                    return "company"
            """)
        project = textwrap.dedent("""
            from conan import ConanFile
            class ProjectBaseConanFile(ConanFile):
                name = "project"
                version = "1.0"

                python_requires = "company/1.0"
                python_requires_extend = "company.CompanyConanFile"

                def msg1(self):
                    return "project"
            """)
        consumer = textwrap.dedent("""
            from conan import ConanFile
            class Base(ConanFile):
                name = "consumer"
                version = "1.0"
                python_requires = "project/1.0"
                python_requires_extend = "project.ProjectBaseConanFile"
                def generate(self):
                    self.output.info("Msg1:{}!!!".format(self.msg1()))
                    self.output.info("Msg2:{}!!!".format(self.msg2()))
                """)
        client.save({"company/conanfile.py": company,
                     "project/conanfile.py": project,
                     "consumer/conanfile.py": consumer})
        client.run("export company")
        client.run("export project")
        client.run("install consumer")
        assert "conanfile.py (consumer/1.0): Msg1:project!!!" in client.out
        assert "conanfile.py (consumer/1.0): Msg2:company!!!" in client.out

    def test_transitive_extend2(self):
        client = TestClient()
        company = textwrap.dedent("""
            from conan import ConanFile
            class CompanyConanFile(ConanFile):
                name = "company"
                version = "1.0"

            class CompanyBase:
                def msg1(self):
                    return "company"
                def msg2(self):
                    return "company"
            """)
        project = textwrap.dedent("""
            from conan import ConanFile
            class ProjectBase:
                def msg1(self):
                    return "project"

            class ProjectBaseConanFile(ConanFile):
                name = "project"
                version = "1.0"
                python_requires = "company/1.0"

                def init(self):
                    pkg_name, base_class_name = "company", "CompanyBase"
                    base_class = getattr(self.python_requires[pkg_name].module, base_class_name)
                    global ProjectBase
                    ProjectBase = type('ProjectBase', (ProjectBase, base_class, object), {})
            """)
        consumer = textwrap.dedent("""
            from conan import ConanFile
            class Base(ConanFile):
                name = "consumer"
                version = "1.0"
                python_requires = "project/1.0"
                python_requires_extend = "project.ProjectBase"
                def generate(self):
                    self.output.info("Msg1:{}!!!".format(self.msg1()))
                    self.output.info("Msg2:{}!!!".format(self.msg2()))
                """)
        client.save({"company/conanfile.py": company,
                     "project/conanfile.py": project,
                     "consumer/conanfile.py": consumer})
        client.run("export company")
        client.run("export project")
        client.run("install consumer")
        assert "conanfile.py (consumer/1.0): Msg1:project!!!" in client.out
        assert "conanfile.py (consumer/1.0): Msg2:company!!!" in client.out
