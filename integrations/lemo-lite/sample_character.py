"""Original example artwork for the layered-character feature: a small robot drawn as aligned full-canvas PNG layers.

Run ``python sample_character.py <empty folder>`` to write the layers; import the folder from the Character tab.
Replace the PNGs with your own layers (same canvas size, same file names) to make your own character.
"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

CANVAS = (600, 700)
STEEL, DARK, LIGHT, ACCENT = (120, 150, 190, 255), (70, 92, 128, 255), (205, 222, 245, 255), (240, 170, 60, 255)


def layer(draw_fn):
    image = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(image))
    return image


def make_layers():
    layers = {}
    layers['body'] = layer(lambda d: (d.rounded_rectangle((200, 330, 400, 560), 40, fill=STEEL, outline=DARK, width=6),
                                      d.ellipse((275, 400, 325, 450), fill=ACCENT, outline=DARK, width=4)))
    layers['head'] = layer(lambda d: (d.rounded_rectangle((190, 110, 410, 310), 50, fill=LIGHT, outline=DARK, width=6),
                                      d.line((300, 110, 300, 70), fill=DARK, width=8), d.ellipse((284, 52, 316, 84), fill=ACCENT)))
    layers['arm_left'] = layer(lambda d: d.rounded_rectangle((140, 340, 195, 500), 25, fill=DARK))
    layers['arm_right'] = layer(lambda d: d.rounded_rectangle((405, 340, 460, 500), 25, fill=DARK))
    layers['leg_left'] = layer(lambda d: (d.rounded_rectangle((225, 555, 285, 665), 22, fill=DARK), d.rounded_rectangle((210, 645, 295, 675), 14, fill=STEEL)))
    layers['leg_right'] = layer(lambda d: (d.rounded_rectangle((315, 555, 375, 665), 22, fill=DARK), d.rounded_rectangle((305, 645, 390, 675), 14, fill=STEEL)))
    layers['tail'] = layer(lambda d: d.polygon([(400, 480), (470, 450), (500, 400), (505, 470), (440, 520)], fill=ACCENT, outline=DARK))
    layers['eyes_open'] = layer(lambda d: (d.ellipse((230, 175, 280, 225), fill=DARK), d.ellipse((320, 175, 370, 225), fill=DARK),
                                           d.ellipse((247, 185, 262, 200), fill='white'), d.ellipse((337, 185, 352, 200), fill='white')))
    layers['eyes_closed'] = layer(lambda d: (d.line((228, 200, 282, 200), fill=DARK, width=8), d.line((318, 200, 372, 200), fill=DARK, width=8)))
    layers['mouth_closed'] = layer(lambda d: d.line((255, 260, 345, 260), fill=DARK, width=8))
    layers['mouth_open'] = layer(lambda d: d.ellipse((265, 240, 335, 285), fill=DARK))
    return layers


def write(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise FileExistsError(f'{folder} is not empty; choose a new folder')
    for name, image in make_layers().items():
        image.save(folder/f'{name}.png')
    return folder


if __name__ == '__main__':
    print('Wrote', write(sys.argv[1]))
