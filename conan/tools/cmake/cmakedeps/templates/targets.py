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
        data_pattern = "${_DIR}/" if not self.generating_module else "${_DIR}/module-"
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
               "configuration": self.cmakedeps.configuration.upper()}

        return ret

    @property
    def template(self):
        return textwrap.dedent("""\
        macro(set_imported_configs target)
            get_property(hasImportedConfigs TARGET ${target} PROPERTY IMPORTED_CONFIGURATIONS DEFINED)
            if (hasImportedConfigs)
                get_target_properties(existingImportedConfigs ${target} IMPORTED_CONFIGURATIONS)
                list(APPEND existingImportedConfigs {{configuration}})
                list(REMOVE_DUPLICATES existingImportedConfigs)
                set_target_properties(${target} IMPORTED_CONFIGURATIONS ${existingImportedConfigs})
            else()
                set_property(TARGET ${target} PROPERTY IMPORTED_CONFIGURATIONS {{configuration}})
            endif()
        endmacro()

        # Load the debug and release variables
        get_filename_component(_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
        file(GLOB DATA_FILES "{{data_pattern}}")

        foreach(f ${DATA_FILES})
            include(${f})
        endforeach()

        # Create the targets for all the components
        foreach(_COMPONENT {{ '${' + pkg_name + '_COMPONENT_NAMES' + '}' }} )
            if(NOT TARGET ${_COMPONENT})
                add_library(${_COMPONENT} INTERFACE IMPORTED)
                message(STATUS "Conan: Component target declared '${_COMPONENT}'")
            endif()
            set_imported_configs(${_COMPONENT})
        endforeach()

        if(NOT TARGET {{ root_target_name }})
            add_library({{ root_target_name }} INTERFACE IMPORTED)
            message(STATUS "Conan: Target declared '{{ root_target_name }}'")
        endif()
        set_imported_configs({{ root_target_name }})

        {%- for alias, target in cmake_target_aliases.items() %}

        if(NOT TARGET {{alias}})
            add_library({{alias}} INTERFACE IMPORTED)
            set_property(TARGET {{ alias }} PROPERTY INTERFACE_LINK_LIBRARIES {{target}})
        else()
            message(WARNING "Target name '{{alias}}' already exists.")
        endif()
        set_imported_configs({{alias}})

        {%- endfor %}

        {%- for comp_name, component_aliases in cmake_component_target_aliases.items() %}

            {%- for alias, target in component_aliases.items() %}

        if(NOT TARGET {{alias}})
            add_library({{alias}} INTERFACE IMPORTED)
            set_property(TARGET {{ alias }} PROPERTY INTERFACE_LINK_LIBRARIES {{target}})
        else()
            message(WARNING "Target name '{{alias}}' already exists.")
        endif()
        set_imported_configs({{alias}})

            {%- endfor %}

        {%- endfor %}

        # Load the debug and release library finders
        get_filename_component(_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
        file(GLOB CONFIG_FILES "${_DIR}/{{ target_pattern }}")

        foreach(f ${CONFIG_FILES})
            include(${f})
        endforeach()

        get_property(isMultiConfig GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
        if(NOT isMultiConfig)
            string(TOUPPER ${CMAKE_BUILD_TYPE} configUpper)
            if(NOT configUpper STREQUAL "{{configuration}}")
                list(APPEND CMAKE_MAP_IMPORTED_CONFIG_${CMAKE_BUILD_TYPE} {{configuration}} )
                list(REMOVE_DUPLICATES CMAKE_MAP_IMPORTED_CONFIG_${CMAKE_BUILD_TYPE})
            endif()
        else()
            foreach(c ${CMAKE_CONFIGURATION_TYPES})
                string(TOUPPER ${c} configUpper)
                if(NOT configUpper STREQUAL "{{configuration}}")
                    list(APPEND CMAKE_MAP_IMPORTED_CONFIG_${configUpper} {{configuration}} )
                    list(REMOVE_DUPLICATES CMAKE_MAP_IMPORTED_CONFIG_${configUpper})
                endif()
            endforeach()
        endif()

        """)
