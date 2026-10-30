"""Compara duas capturas pixel a pixel. Uso: python3 diff.py original.png integrado.png saida-diff.png
Imprime o percentual de pixels diferentes (tolerância 16 por canal) e grava a imagem com as diferenças em vermelho."""
import sys
from PIL import Image, ImageChops

a, b, saida = sys.argv[1:4]
ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
w, h = max(ia.width, ib.width), max(ia.height, ib.height)
pa, pb = Image.new("RGB", (w, h)), Image.new("RGB", (w, h))
pa.paste(ia), pb.paste(ib)
mascara = ImageChops.difference(pa, pb).convert("L").point(lambda v: 255 if v > 16 else 0)
diferentes = mascara.tobytes().count(255)
marcado = Image.blend(pb, Image.new("RGB", (w, h), (255, 0, 0)), 0.0)
marcado.paste((255, 0, 0), mask=mascara)
marcado.save(saida)
print(f"{diferentes / (w * h) * 100:6.2f}% diferente | tamanhos {ia.size} vs {ib.size}")
