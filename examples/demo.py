import logging
import os

from pixel_font_build_tools import DesignContext

logging.basicConfig(level=logging.DEBUG)

project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
glyphs_dir = os.path.join(project_root_dir, 'assets', 'glyphs')
outputs_dir = os.path.join(project_root_dir, 'build', 'outputs')

width_modes = [
    'monospaced',
    'proportional',
]

language_flavors = [
    'latin',
    'zh_cn',
    'zh_hk',
    'zh_tw',
    'zh_tr',
    'ja',
    'ko',
]


def main():
    context = DesignContext.load(glyphs_dir, defined_dir_flavors=width_modes, defined_name_flavors=language_flavors)
    context.standardize_glyph_files()
    context.fallback_default_name_flavor()
    for weight_mode in width_modes:
        context.get_sequence(weight_mode)
        context.get_sequence()
        context.get_alphabet(weight_mode)
        context.get_alphabet()
        for language_flavor in language_flavors:
            context.get_character_mapping(weight_mode, language_flavor)
            context.get_character_mapping()
            context.get_glyph_file_infos(weight_mode, [language_flavor])
            context.get_glyph_file_infos(weight_mode)
            context.get_glyph_file_infos()
    print()


if __name__ == '__main__':
    main()
