import logging
import os

import unidata_blocks

from pixel_font_build_tools.utils import glyph_util, fs_util

logger = logging.getLogger('pixel_font_build_tools.context')

_HEX_NAME_NOTDEF = 'notdef'
_DEFAULT_DIR_FLAVOR = 'common'
_DEFAULT_NAME_FLAVOR = 'default'


class GlyphFileInfo:
    @staticmethod
    def by(
            file_dir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            file_name: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            dir_flavor: str,
            defined_name_flavors: list[str] | None,
    ) -> 'GlyphFileInfo':
        file_path = os.path.join(file_dir, file_name)
        file_name = file_name.lower()
        assert file_name.endswith('.png'), f"Glyph file not '.png' file: '{file_path}'"
        tokens = file_name.removesuffix('.png').split(' ', 1)

        hex_name = tokens[0].strip()
        if hex_name == _HEX_NAME_NOTDEF:
            code_point = -1
        else:
            code_point = int(tokens[0].strip(), 16)

        name_flavors = []
        if len(tokens) == 2:
            for name_flavor in tokens[1].split(','):
                name_flavor = name_flavor.strip()
                if defined_name_flavors is not None:
                    assert name_flavor in defined_name_flavors, f"Undefined name flavor '{name_flavor}': '{file_path}'"
                if name_flavor not in name_flavors:
                    name_flavors.append(name_flavor)
            if defined_name_flavors is not None:
                name_flavors.sort(key=lambda x: defined_name_flavors.index(x))

        return GlyphFileInfo(file_path, code_point, dir_flavor, name_flavors)

    def __init__(
            self,
            file_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            code_point: int,
            dir_flavor: str,
            name_flavors: list[str],
    ):
        self.file_path = file_path
        self.code_point = code_point
        self.dir_flavor = dir_flavor
        self.name_flavors = name_flavors
        self.glyph_data, self.glyph_width, self.glyph_height = glyph_util.load_glyph_data_from_png(file_path)
        logger.debug("Load glyph data: '%s'", file_path)

    def save_glyph_data(self):
        glyph_util.save_glyph_data_to_png(self.glyph_data, self.file_path)
        logger.debug("Save glyph data: '%s'", self.file_path)


class GlyphInfo:
    def __init__(self, code_point: int):
        self.code_point = code_point
        self.file_info_registry: dict[str, dict[str, GlyphFileInfo]] = {}

    def add_glyph_file_info(self, file_info: GlyphFileInfo):
        dir_flavor = file_info.dir_flavor
        if dir_flavor in self.file_info_registry:
            dir_flavor_registry = self.file_info_registry[dir_flavor]
        else:
            dir_flavor_registry = {}
            self.file_info_registry[dir_flavor] = dir_flavor_registry

        name_flavors = file_info.name_flavors
        if len(name_flavors) == 0:
            name_flavor = _DEFAULT_NAME_FLAVOR
            assert name_flavor not in dir_flavor_registry, f"Glyph file default name flavor already exists:\n'{file_info.file_path}'\n'{dir_flavor_registry[name_flavor].file_path}'"
            dir_flavor_registry[name_flavor] = file_info
        else:
            for name_flavor in name_flavors:
                assert name_flavor not in dir_flavor_registry, f"Glyph file name flavor '{name_flavor}' already exists:\n'{file_info.file_path}'\n'{dir_flavor_registry[name_flavor].file_path}'"
                dir_flavor_registry[name_flavor] = file_info


class DesignContext:
    @staticmethod
    def load(
            root_dir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            defined_dir_flavors: list[str] = None,
            defined_name_flavors: list[str] = None,
    ) -> 'DesignContext':
        code_point_to_glyph_info = {}
        path_to_glyph_file_info = {}
        for dir_flavor in os.listdir(root_dir):
            dir_flavor_path = os.path.join(root_dir, dir_flavor)
            if not os.path.isdir(dir_flavor_path):
                continue
            if dir_flavor != _DEFAULT_DIR_FLAVOR and defined_dir_flavors is not None:
                assert dir_flavor in defined_dir_flavors, f"Undefined dir flavor: '{dir_flavor}'"
            for file_dir, _, file_names in os.walk(dir_flavor_path):
                for file_name in file_names:
                    if not file_name.endswith('.png'):
                        continue
                    file_info = GlyphFileInfo.by(file_dir, file_name, dir_flavor, defined_name_flavors)
                    code_point = file_info.code_point
                    if code_point in code_point_to_glyph_info:
                        glyph_info = code_point_to_glyph_info[code_point]
                    else:
                        glyph_info = GlyphInfo(code_point)
                        code_point_to_glyph_info[code_point] = glyph_info
                    glyph_info.add_glyph_file_info(file_info)
                    path_to_glyph_file_info[str(file_info.file_path)] = file_info
        return DesignContext(
            root_dir,
            defined_dir_flavors,
            defined_name_flavors,
            code_point_to_glyph_info,
            path_to_glyph_file_info,
        )

    def __init__(
            self,
            root_dir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            defined_dir_flavors: list[str] | None,
            defined_name_flavors: list[str] | None,
            code_point_to_glyph_info: dict[int, GlyphInfo],
            path_to_glyph_file_info: dict[str, GlyphFileInfo],
    ):
        self.root_dir = root_dir
        self.defined_dir_flavors = defined_dir_flavors
        self.defined_name_flavors = defined_name_flavors
        self.code_point_to_glyph_info = code_point_to_glyph_info
        self.path_to_glyph_file_info = path_to_glyph_file_info

    def standardize_glyph_files(self):
        for old_file_dir, _, old_file_names in list(os.walk(self.root_dir, topdown=False)):
            for old_file_name in old_file_names:
                if not old_file_name.endswith('.png'):
                    continue
                old_file_path = os.path.join(old_file_dir, old_file_name)
                file_info = self.path_to_glyph_file_info[old_file_path]
                file_info.save_glyph_data()

                code_point = file_info.code_point
                if code_point == -1:
                    hex_name = _HEX_NAME_NOTDEF
                else:
                    hex_name = f'{code_point:04X}'
                name_flavors = file_info.name_flavors
                file_name = f'{hex_name}{"" if len(name_flavors) == 0 else " "}{",".join(name_flavors)}.png'
                file_dir = os.path.join(self.root_dir, file_info.dir_flavor)
                if code_point != -1:
                    block = unidata_blocks.get_block_by_code_point(code_point)
                    block_dir_name = f'{block.code_start:04X}-{block.code_end:04X} {block.name}'
                    if block.code_start == 0x4E00:  # CJK Unified Ideographs
                        block_dir_name = os.path.join(block_dir_name, f'{hex_name[0:-2]}-')
                    file_dir = os.path.join(file_dir, block_dir_name)
                file_path = os.path.join(file_dir, file_name)

                if file_path != old_file_path:
                    assert not os.path.exists(file_path), f"Glyph file duplicate:\n'{file_path}'\n'{old_file_path}'"
                    fs_util.make_dirs(file_dir)
                    os.rename(old_file_path, file_path)
                    file_info.file_path = file_path
                    self.path_to_glyph_file_info.pop(old_file_path)
                    self.path_to_glyph_file_info[file_path] = file_info
                    logger.debug("Fix glyph file path:\nfrom '%s'\nto   '%s'", old_file_path, file_path)

            other_file_names = os.listdir(old_file_dir)
            if '.DS_Store' in other_file_names:
                os.remove(os.path.join(old_file_dir, '.DS_Store'))
                other_file_names.remove('.DS_Store')
            if len(other_file_names) == 0:
                os.rmdir(old_file_dir)
