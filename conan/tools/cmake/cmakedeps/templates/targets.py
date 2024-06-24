import textwrap

from conan.tools.cmake.cmakedeps.templates import CMakeDepsFileTemplate

"""

FooTargets.cmake

"""


class TargetsTemplate(CMakeDepsFileTemplate):

    @property
    def filename(self):
        name = "" if not self.generating_module else "module-"
        name += self.file_name + "Targets.cmake"
        return name

    @property
    def context(self):
        data_pattern = "${CMAKE_CURRENT_LIST_DIR}/" if not self.generating_module else "${CMAKE_CURRENT_LIST_DIR}/module-"
        data_pattern += "{}-*-data.cmake".format(self.file_name)

        target_pattern = "" if not self.generating_module else "module-"
        target_pattern += "{}-Target-*.cmake".format(self.file_name)

        cmake_target_aliases = self.conanfile.cpp_info.\
            get_property("cmake_target_aliases") or dict()

        target = self.root_target_name
        cmake_target_aliases = {alias: target for alias in cmake_target_aliases}

        cmake_component_target_aliases = dict()
        for comp_name in self.conanfile.cpp_info.components:
            if comp_name is not None:
                aliases = \
                    self.conanfile.cpp_info.components[comp_name].\
                    get_property("cmake_target_aliases") or dict()

                target = self.get_component_alias(self.conanfile, comp_name)
                cmake_component_target_aliases[comp_name] = {alias: target for alias in aliases}

        ret = {"pkg_name": self.pkg_name,
               "root_target_name": self.root_target_name,
               "file_name": self.file_name,
               "data_pattern": data_pattern,
               "target_pattern": target_pattern,
               "cmake_target_aliases": cmake_target_aliases,
               "cmake_component_target_aliases": cmake_component_target_aliases,
               "cmake_component_target_name": self.file_name}

        return ret

    @property
    def template(self):
        return textwrap.dedent("""\
        macro(set_imported_configs target foundConfs)
            get_property(hasImportedConfigs TARGET ${target} PROPERTY IMPORTED_CONFIGURATIONS DEFINED)
            if (hasImportedConfigs)
                get_target_properties(existingImportedConfigs ${target} IMPORTED_CONFIGURATIONS)
                list(APPEND existingImportedConfigs ${foundConfs})
                list(REMOVE_DUPLICATES existingImportedConfigs)
                set_target_properties(${target} IMPORTED_CONFIGURATIONS ${existingImportedConfigs})
            else()
                set_property(TARGET ${target} PROPERTY IMPORTED_CONFIGURATIONS ${foundConfs})
            endif()
            get_target_property(existingConfigs ${target} IMPORTED_CONFIGURATIONS)
            if ("RELEASE" IN_LIST existingConfigs)
                if (NOT "MINSIZEREL" IN_LIST existingConfigs)
                    set_property(TARGET ${target} PROPERTY MAP_IMPORTED_CONFIG_MINSIZEREL Release)
                endif()
                if (NOT "RELWITHDEBINFO" IN_LIST existingConfigs)
                    set_property(TARGET ${target} PROPERTY MAP_IMPORTED_CONFIG_RELWITHDEBINFO Release)
                endif()
            endif()
            if ("MINSIZEREL" IN_LIST existingConfigs)
                if (NOT "RELEASE" IN_LIST existingConfigs)
                    set_property(TARGET ${target}PROPERTY MAP_IMPORTED_CONFIG_RELEASE MinSizeRel)
                endif()
                if (NOT "RELWITHDEBINFO" IN_LIST existingConfigs)
                    set_property(TARGET ${target} PROPERTY MAP_IMPORTED_CONFIG_RELWITHDEBINFO MinSizeRel)
                endif()
            endif()
            if ("RELWITHDEBINFO" IN_LIST existingConfigs)
                if (NOT "MINSIZEREL" IN_LIST existingConfigs)
                    set_property(TARGET ${target} PROPERTY MAP_IMPORTED_CONFIG_MINSIZEREL RelWithDebInfo)
                endif()
                if (NOT "RELEASE" IN_LIST existingConfigs)
                    set_property(TARGET ${target} PROPERTY MAP_IMPORTED_CONFIG_RELEASE RelWithDebInfo)
                endif()
            endif()
        endmacro()

        # Load the debug and release variables
        get_filename_component(_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
        file(GLOB DATA_FILES LIST_DIRECTORIES false "{{data_pattern}}")
                               
        # Figure out the available configurations
        set(allConfigs "")
        foreach(fn ${DATA_FILES})
            if (fn MATCHES ".*{{cmake_component_target_name}}-(.*)-.*-.*data\\\\.cmake")
                string(TOUPPER "${CMAKE_MATCH_1}" upMatch)
                list(APPEND allConfigs ${upMatch})
            endif()
        endforeach()
        list(REMOVE_DUPLICATES allConfigs)
        message({% raw %}${{% endraw %}{{ file_name }}_MESSAGE_MODE} "Found configurations ${allConfigs}")

        foreach(f ${DATA_FILES})
            include(${f})
        endforeach()

        # Create the targets for all the components
        foreach(_COMPONENT {{ '${' + pkg_name + '_COMPONENT_NAMES' + '}' }} )
            if(NOT TARGET ${_COMPONENT})
                add_library(${_COMPONENT} INTERFACE IMPORTED)
                message({% raw %}${{% endraw %}{{ file_name }}_MESSAGE_MODE} "Conan: Component target declared '${_COMPONENT}'")
            endif()
            set_imported_configs(${_COMPONENT} "${allConfigs}")
        endforeach()

        if(NOT TARGET {{ root_target_name }})
            add_library({{ root_target_name }} INTERFACE IMPORTED)
            message({% raw %}${{% endraw %}{{ file_name }}_MESSAGE_MODE} "Conan: Target declared '{{ root_target_name }}'")
        endif()
        set_imported_configs({{ root_target_name }} "${allConfigs}")

        {%- for alias, target in cmake_target_aliases.items() %}

        if(NOT TARGET {{alias}})
            add_library({{alias}} INTERFACE IMPORTED)
            set_property(TARGET {{ alias }} PROPERTY INTERFACE_LINK_LIBRARIES {{target}})
        endif()
        set_imported_configs({{alias}} "${allConfigs}")

        {%- endfor %}

        {%- for comp_name, component_aliases in cmake_component_target_aliases.items() %}

            {%- for alias, target in component_aliases.items() %}

        if(NOT TARGET {{alias}})
            add_library({{alias}} INTERFACE IMPORTED)
            set_property(TARGET {{ alias }} PROPERTY INTERFACE_LINK_LIBRARIES {{target}})
        endif()
        set_imported_configs({{alias}} "${allConfigs}")

            {%- endfor %}

        {%- endfor %}

        # Load the debug and release library finders
        get_filename_component(_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
        file(GLOB CONFIG_FILES "${_DIR}/{{ target_pattern }}")

        foreach(f ${CONFIG_FILES})
            include(${f})
        endforeach()

        """)
