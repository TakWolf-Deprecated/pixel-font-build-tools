import logging
import math
import os
from types import SimpleNamespace

from pixel_font_builder import FontCollectionBuilder, Glyph, FontBuilder, StyleName, SerifMode
from pixel_font_builder.opentype import Flavor

from pixel_font_build_tools import DesignContext
from pixel_font_build_tools.utils import fs_util

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('demo')

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

font_size = 12

width_mode_to_layout_params = {
    'monospaced': SimpleNamespace(
        ascent=10,
        descent=-2,
        x_height=6,
        cap_height=8,
    ),
    'proportional': SimpleNamespace(
        ascent=14,
        descent=-4,
        x_height=6,
        cap_height=9,
    ),
}


def _create_builder(
        context: DesignContext,
        glyph_cacher: dict[str, Glyph],
        width_mode: str,
        language_flavor: str,
        is_collection: bool,
) -> FontBuilder:
    builder = FontBuilder(font_size)

    family_name = 'Demo Pixel'
    builder.meta_info.version = '1.0.0'
    builder.meta_info.family_name = f'{family_name} {width_mode.capitalize()} {language_flavor}'
    builder.meta_info.style_name = StyleName.REGULAR
    builder.meta_info.serif_mode = SerifMode.SANS_SERIF
    builder.meta_info.width_mode = width_mode.capitalize()
    builder.meta_info.manufacturer = 'Pixel Font Studio'
    builder.meta_info.designer = 'TakWolf'
    builder.meta_info.description = 'A demo pixel font.'
    builder.meta_info.copyright_info = 'Copyright (c) TakWolf'
    builder.meta_info.license_info = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
    builder.meta_info.vendor_url = 'https://github.com/TakWolf/pixel-font-build-tools'
    builder.meta_info.designer_url = 'https://takwolf.com'
    builder.meta_info.license_url = 'https://scripts.sil.org/OFL'
    builder.meta_info.sample_text = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n我们度过的每个平凡的日常，也许就是连续发生的奇迹。\n我們度過的每個平凡的日常，也許就是連續發生的奇蹟。'

    if is_collection:
        builder.opentype_config.cff_family_name = f'{family_name} {width_mode.capitalize()}'

    layout_params = width_mode_to_layout_params[width_mode]

    builder.horizontal_header.ascent = layout_params.ascent
    builder.horizontal_header.descent = layout_params.descent

    builder.vertical_header.ascent = layout_params.ascent
    builder.vertical_header.descent = layout_params.descent

    builder.os2_config.x_height = layout_params.x_height
    builder.os2_config.cap_height = layout_params.cap_height

    character_mapping = context.get_character_mapping(width_mode, language_flavor)
    builder.character_mapping.update(character_mapping)

    glyph_files = context.get_glyph_files(width_mode, None if is_collection else [language_flavor])
    for glyph_file in glyph_files:
        if glyph_file.file_path in glyph_cacher:
            glyph = glyph_cacher[glyph_file.file_path]
        else:
            horizontal_origin_y = math.floor((layout_params.ascent + layout_params.descent - glyph_file.glyph_height) / 2)
            vertical_origin_y = (glyph_file.glyph_height - font_size) // 2
            glyph = Glyph(
                name=glyph_file.glyph_name,
                advance_width=glyph_file.glyph_width,
                advance_height=font_size,
                horizontal_origin=(0, horizontal_origin_y),
                vertical_origin_y=vertical_origin_y,
                data=glyph_file.glyph_data,
            )
            glyph_cacher[glyph_file.file_path] = glyph
        builder.glyphs.append(glyph)

    return builder


def make_font_files(context: DesignContext, width_mode: str):
    glyph_cacher = {}

    for language_flavor in language_flavors:
        builder = _create_builder(context, glyph_cacher, width_mode, language_flavor, is_collection=False)

        otf_file_path = os.path.join(outputs_dir, f'demo-{width_mode}-{language_flavor}.otf')
        builder.save_otf(otf_file_path)
        logger.info("Make font file: '%s'", otf_file_path)

        woff2_file_path = os.path.join(outputs_dir, f'demo-{width_mode}-{language_flavor}.woff2')
        builder.save_otf(woff2_file_path, flavor=Flavor.WOFF2)
        logger.info("Make font file: '%s'", woff2_file_path)

        ttf_file_path = os.path.join(outputs_dir, f'demo-{width_mode}-{language_flavor}.ttf')
        builder.save_ttf(ttf_file_path)
        logger.info("Make font file: '%s'", ttf_file_path)

        bdf_file_path = os.path.join(outputs_dir, f'demo-{width_mode}-{language_flavor}.bdf')
        builder.save_bdf(bdf_file_path)
        logger.info("Make font file: '%s'", bdf_file_path)

    collection_builder = FontCollectionBuilder()
    for language_flavor in language_flavors:
        builder = _create_builder(context, glyph_cacher, width_mode, language_flavor, is_collection=True)
        collection_builder.font_builders.append(builder)

    otc_file_path = os.path.join(outputs_dir, f'demo-{width_mode}.otc')
    collection_builder.save_otc(otc_file_path)
    logger.info("Make font collection file: '%s'", otc_file_path)

    ttc_file_path = os.path.join(outputs_dir, f'demo-{width_mode}.ttc')
    collection_builder.save_ttc(ttc_file_path)
    logger.info("Make font collection file: '%s'", ttc_file_path)


def main():
    fs_util.delete_dir(outputs_dir)
    fs_util.make_dirs(outputs_dir)

    context = DesignContext.load(glyphs_dir, defined_dir_flavors=width_modes, defined_name_flavors=language_flavors)
    context.standardize_glyph_files()
    for weight_mode in width_modes:
        make_font_files(context, weight_mode)


if __name__ == '__main__':
    main()
