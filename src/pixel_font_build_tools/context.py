import logging
import os
from collections import defaultdict

import unidata_blocks

from pixel_font_build_tools.utils import glyph_util, fs_util

logger = logging.getLogger('pixel_font_build_tools.context')


class GlyphFile:
    @staticmethod
    def load(
            file_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            dir_flavor: str,
            defined_name_flavors: list[str],
    ) -> 'GlyphFile':
        assert file_path.endswith('.png'), f"Glyph file not a '.png' file: '{file_path}'"

        tokens = os.path.basename(file_path).removesuffix('.png').split(' ', 1)
        code_point = glyph_util.hex_name_to_code_point(tokens[0].strip())
        name_flavors = []
        if len(tokens) == 2:
            for name_flavor in tokens[1].split(','):
                name_flavor = name_flavor.lower().strip()
                assert name_flavor in defined_name_flavors, f"Glyph file undefined name flavor '{name_flavor}': '{file_path}'"
                if name_flavor not in name_flavors:
                    name_flavors.append(name_flavor)
            name_flavors.sort(key=lambda x: defined_name_flavors.index(x))

        return GlyphFile(file_path, code_point, dir_flavor, name_flavors)

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

    @property
    def glyph_name(self) -> str:
        if self.code_point == -1:
            glyph_name = '.notdef'
        else:
            glyph_name = f'uni{self.code_point:04X}'
        if len(self.name_flavors) != 0:
            glyph_name = f'{glyph_name}-{self.name_flavors[0]}'
        return glyph_name

    def save(self):
        glyph_util.save_glyph_data_to_png(self.glyph_data, self.file_path)


class GlyphInfo:
    def __init__(self, code_point: int):
        self.code_point = code_point
        self._dir_flavor_registry: dict[str, dict[str, GlyphFile]] = defaultdict(dict)

    def add_glyph_file(self, glyph_file: GlyphFile):
        name_flavor_registry = self._dir_flavor_registry[glyph_file.dir_flavor]
        if len(glyph_file.name_flavors) == 0:
            assert '' not in name_flavor_registry, f"Glyph file default name flavor already exists:\n'{glyph_file.file_path}'\n'{name_flavor_registry[''].file_path}'"
            name_flavor_registry[''] = glyph_file
        else:
            for name_flavor in glyph_file.name_flavors:
                assert name_flavor not in name_flavor_registry, f"Glyph file name flavor '{name_flavor}' already exists:\n'{glyph_file.file_path}'\n'{name_flavor_registry[name_flavor].file_path}'"
                name_flavor_registry[name_flavor] = glyph_file

    def fallback_default_name_flavor(self, defined_name_flavors: list[str]):
        for name_flavor_registry in self._dir_flavor_registry.values():
            if '' in name_flavor_registry:
                continue
            for name_flavor in defined_name_flavors:
                if name_flavor in name_flavor_registry:
                    glyph_file = name_flavor_registry[name_flavor]
                    for exist_name_flavor in glyph_file.name_flavors:
                        assert name_flavor_registry.pop(exist_name_flavor) == glyph_file
                    glyph_file.name_flavors.clear()
                    name_flavor_registry[''] = glyph_file
                    break

    def query_by_dir_flavor(self, dir_flavor: str = 'common') -> dict[str, GlyphFile] | None:
        if dir_flavor in self._dir_flavor_registry:
            return self._dir_flavor_registry[dir_flavor]
        elif 'common' in self._dir_flavor_registry:
            return self._dir_flavor_registry['common']
        else:
            return None


class DesignContext:
    @staticmethod
    def load(
            root_dir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            defined_dir_flavors: list[str] = None,
            defined_name_flavors: list[str] = None,
    ) -> 'DesignContext':
        if defined_dir_flavors is None:
            defined_dir_flavors = []
        if defined_name_flavors is None:
            defined_name_flavors = []

        code_point_to_glyph_info = {}
        path_to_glyph_file = {}

        for dir_flavor in os.listdir(root_dir):
            dir_flavor_path = os.path.join(root_dir, dir_flavor)
            if not os.path.isdir(dir_flavor_path):
                continue
            if dir_flavor != 'common':
                assert dir_flavor in defined_dir_flavors, f"Undefined dir flavor: '{dir_flavor}'"
            for file_dir, _, file_names in os.walk(dir_flavor_path):
                for file_name in file_names:
                    if not file_name.endswith('.png'):
                        continue
                    file_path = os.path.join(file_dir, file_name)
                    glyph_file = GlyphFile.load(file_path, dir_flavor, defined_name_flavors)
                    code_point = glyph_file.code_point
                    if code_point in code_point_to_glyph_info:
                        glyph_info = code_point_to_glyph_info[code_point]
                    else:
                        glyph_info = GlyphInfo(code_point)
                        code_point_to_glyph_info[code_point] = glyph_info
                    glyph_info.add_glyph_file(glyph_file)
                    path_to_glyph_file[str(glyph_file.file_path)] = glyph_file

        return DesignContext(
            root_dir,
            defined_dir_flavors,
            defined_name_flavors,
            code_point_to_glyph_info,
            path_to_glyph_file,
        )

    def __init__(
            self,
            root_dir: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            defined_dir_flavors: list[str],
            defined_name_flavors: list[str],
            code_point_to_glyph_info: dict[int, GlyphInfo],
            path_to_glyph_file: dict[str, GlyphFile],
    ):
        self.root_dir = root_dir
        self.defined_dir_flavors = defined_dir_flavors
        self.defined_name_flavors = defined_name_flavors
        self.code_point_to_glyph_info = code_point_to_glyph_info
        self.path_to_glyph_file = path_to_glyph_file

        self._sequence_cacher: dict[str, list[int]] = {}
        self._alphabet_cacher: dict[str, list[str]] = {}
        self._character_mapping_cacher: dict[(str, str), dict[int, str]] = {}
        self._glyph_files_cacher: dict[(str, str | None), list[GlyphFile]] = {}

    def standardize_glyph_files(self):
        for old_file_dir, _, old_file_names in list(os.walk(self.root_dir, topdown=False)):
            for old_file_name in old_file_names:
                if not old_file_name.endswith('.png'):
                    continue
                old_file_path = os.path.join(old_file_dir, old_file_name)
                assert old_file_path in self.path_to_glyph_file, f"Unmatched glyph file: '{old_file_path}'"
                glyph_file = self.path_to_glyph_file[old_file_path]
                glyph_file.save()

                code_point = glyph_file.code_point
                hex_name = glyph_util.code_point_to_hex_name(glyph_file.code_point)
                name_flavors = glyph_file.name_flavors
                file_name = f'{hex_name}{"" if len(name_flavors) == 0 else " "}{",".join(name_flavors)}.png'
                file_dir = os.path.join(self.root_dir, glyph_file.dir_flavor)
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
                    glyph_file.file_path = file_path
                    self.path_to_glyph_file.pop(old_file_path)
                    self.path_to_glyph_file[file_path] = glyph_file
                    logger.debug("Fix glyph file path:\nfrom '%s'\nto   '%s'", old_file_path, file_path)

            other_file_names = os.listdir(old_file_dir)
            if '.DS_Store' in other_file_names:
                os.remove(os.path.join(old_file_dir, '.DS_Store'))
                other_file_names.remove('.DS_Store')
            if len(other_file_names) == 0:
                os.rmdir(old_file_dir)

    def fallback_default_name_flavor(self):
        for glyph_info in self.code_point_to_glyph_info.values():
            glyph_info.fallback_default_name_flavor(self.defined_name_flavors)

    def _check_dir_flavor_validity(self, dir_flavor: str):
        if dir_flavor != 'common':
            assert dir_flavor in self.defined_dir_flavors, f"Undefined dir flavor: '{dir_flavor}'"

    def _check_name_flavor_validity(self, name_flavor: str):
        if name_flavor != '':
            assert name_flavor in self.defined_name_flavors, f"Undefined name flavor: '{name_flavor}'"

    def get_sequence(self, dir_flavor: str = 'common') -> list[int]:
        self._check_dir_flavor_validity(dir_flavor)
        if dir_flavor in self._sequence_cacher:
            sequence = self._sequence_cacher[dir_flavor]
        else:
            sequence = []
            for glyph_info in self.code_point_to_glyph_info.values():
                if glyph_info.query_by_dir_flavor(dir_flavor) is not None:
                    sequence.append(glyph_info.code_point)
            sequence.sort()
            self._sequence_cacher[dir_flavor] = sequence
        return sequence

    def get_alphabet(self, dir_flavor: str = 'common') -> list[str]:
        self._check_dir_flavor_validity(dir_flavor)
        if dir_flavor in self._alphabet_cacher:
            alphabet = self._alphabet_cacher[dir_flavor]
        else:
            alphabet = [chr(code_point) for code_point in self.get_sequence(dir_flavor) if code_point != -1]
            self._alphabet_cacher[dir_flavor] = alphabet
        return alphabet

    def get_character_mapping(
            self,
            dir_flavor: str = 'common',
            name_flavor: str = '',
    ) -> dict[int, str]:
        self._check_dir_flavor_validity(dir_flavor)
        self._check_name_flavor_validity(name_flavor)
        cache_name = dir_flavor, name_flavor
        if cache_name in self._character_mapping_cacher:
            character_mapping = self._character_mapping_cacher[cache_name]
        else:
            character_mapping = {}
            for code_point, glyph_info in self.code_point_to_glyph_info.items():
                if code_point == -1:
                    continue
                name_flavor_registry = glyph_info.query_by_dir_flavor(dir_flavor)
                if name_flavor_registry is not None:
                    glyph_file = name_flavor_registry.get(name_flavor, name_flavor_registry.get('', None))
                    assert glyph_file is not None, f"No default name flavor: '{dir_flavor} {code_point:04X}'"
                    character_mapping[code_point] = glyph_file.glyph_name
            self._character_mapping_cacher[cache_name] = character_mapping
        return character_mapping

    def get_glyph_files(
            self,
            dir_flavor: str = 'common',
            name_flavors: list[str] = None,
    ) -> list[GlyphFile]:
        self._check_dir_flavor_validity(dir_flavor)
        if name_flavors is None:
            name_flavors = self.defined_name_flavors
        else:
            for name_flavor in name_flavors:
                self._check_name_flavor_validity(name_flavor)
        cache_name = dir_flavor, ','.join(name_flavors)
        if cache_name is self._glyph_files_cacher:
            glyph_files = self._glyph_files_cacher[cache_name]
        else:
            glyph_files = []
            sequence = self.get_sequence(dir_flavor)
            for name_flavor in name_flavors:
                for code_point in sequence:
                    glyph_info = self.code_point_to_glyph_info[code_point]
                    name_flavor_registry = glyph_info.query_by_dir_flavor(dir_flavor)
                    assert name_flavor_registry is not None
                    glyph_file = name_flavor_registry.get(name_flavor, name_flavor_registry.get('', None))
                    assert glyph_file is not None, f"No default name flavor: '{dir_flavor} {code_point:04X}'"
                    if glyph_file not in glyph_files:
                        glyph_files.append(glyph_file)
            self._glyph_files_cacher[cache_name] = glyph_files
        return glyph_files
