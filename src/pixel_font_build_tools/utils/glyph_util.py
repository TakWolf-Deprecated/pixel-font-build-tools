import os

import png


def load_glyph_data_from_png(
        file_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
) -> tuple[list[list[int]], int, int]:
    width, height, bitmap, _ = png.Reader(filename=file_path).read()
    data = []
    for bitmap_row in bitmap:
        data_row = []
        for x in range(0, width * 4, 4):
            alpha = bitmap_row[x + 3]
            if alpha > 127:
                data_row.append(1)
            else:
                data_row.append(0)
        data.append(data_row)
    return data, width, height


def save_glyph_data_to_png(
        data: list[list[int]],
        file_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
):
    bitmap = []
    for data_row in data:
        bitmap_row = []
        for x in data_row:
            bitmap_row.append(0)
            bitmap_row.append(0)
            bitmap_row.append(0)
            if x == 0:
                bitmap_row.append(0)
            else:
                bitmap_row.append(255)
        bitmap.append(bitmap_row)
    png.from_array(bitmap, 'RGBA').save(file_path)


def hex_name_to_code_point(hex_name: str) -> int:
    if hex_name == 'notdef':
        code_point = -1
    else:
        code_point = int(hex_name, 16)
    return code_point


def code_point_to_hex_name(code_point: int) -> str:
    if code_point == -1:
        hex_name = 'notdef'
    else:
        hex_name = f'{code_point:04X}'
    return hex_name
