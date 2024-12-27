"""Operaciones para los bloques de color en el lado derecho de la paleta.

Cajas definidas por una dist de enteros. Por ejemplo, [1, 1, 1, 1, 1, 2] crearía una
pila de bloques de color donde los primeros cincos tienen la misma altura y el último
es el doble de alto.

Yo doblando esta regla por estética. Primero, agrupando los últimos 1s consecutivos
en una pila vertical.

00000
11111
22222
33 44
55555

En segundo lugar, intentanda haces todas las pilas verticales la misma altura. En
tercer lugar, intentando mentener todas las dist=1 a la misma altura. Donde sea, solo
dist valores > 1 serán estirados.

:author: Shay Hill
:created: 2024-11-20
"""

import dataclasses
import itertools as it
import math
from collections.abc import Iterable, Iterator, Sequence

import svg_ultralight as su
from basic_colormath import rgb_to_hex

from palette_image import geometry as geo
from palette_image.colornames import get_colornames
from palette_image.partition_colors import (
    fit_partition_to_distribution,
    fit_partition_to_distribution_with_slivers,
)

AVANT_GARDE_SLICES = 12
SLIVER_SLICES = 24


def color_to_hex(color: tuple[float, float, float] | str) -> str:
    """Convertir un color a una cadena hexadecimal.

    :param color: un color como una tupla RGB o una cadena hexadecimal con o sin el
        signo "#"
    :return: una cadena hexadecimal con el signo "#"
    """
    if isinstance(color, str):
        return "#" + color.lstrip("#")
    return rgb_to_hex(color)


def _group_double_1s(slices: list[int]) -> list[list[int]]:
    """Trabajando desde el final de una lists, agrupa los primeros dos 1s consecutivos.

    :param slices: una lista de enteros
    :return: una lista de listas de enteros, donde cada liste es un solo entero o
        [1, 1]

    Dada una lista de números enteros, cuando aparezca 1, 1, agrúpelos como [1, 1].
    Agrupar otros valores como solteros.

        >>> _group_double_1s([1, 2, 3, 4, 1, 1])
        [[1], [2], [3], [4], [1, 1]]

    Comienza desde -1 y se detiente después  de crear el primer [1, 1].

    slices = [1, 1, 1, 1, 1, 2] -> [[1], [1], [1], [1, 1], [2]]
    """
    groups: list[list[int]] = []
    for i in reversed(slices):
        if any(len(x) > 1 for x in groups):
            groups.append([i])
            continue
        if i == 1 and groups and groups[-1] == [1]:
            groups[-1].append(1)
        else:
            groups.append([i])
    return list(reversed(groups))


def _divvy_height(
    bbox: su.BoundingBox,
    groups: list[list[int]],
    *,
    locks: Sequence[tuple[list[int], float]] | None = None,
) -> list[float]:
    """Divide a height into segments based on vertical groupings.

    Dividir una altura en segmentos basados en agrupaciones verticales.

    :param bbox: la BoundingBox para dividar verticalmente
    :param groups: una lista de agrapaciones horizontales. La salida de
        _group_double_1s
    :param locks: una lista de tuplas. Cada tuple es un grupo y una altura. Para
        cualquier g, h en locks, la altura de g se establecerá en h. Si None, el
        valor predeterminando es establecer [1] en la mitad del ancho y [1, 1] en el
        ancho completo. Enumere los bloqueos en orden de prioridad, comenzando por el
        de mayor prioridad. Si todos grupos están bloqueados, no habrá ningún grupo
        para escalar para llenar la altura del bbox, por lo que divvy_height
        eliminará los bloqueos de la derecha de la secuencia de bloqueo hasta que se
        encuentren grupos escalables.

    :return: una lista de alturas que suman bbox.height

    _group_double_1s agrupará 1 consecutivos en una dists en un doble. Esto imita
    algunas de las primeras imágenes de palata en mi proyecto. Los valores posibles
    son [[3], [4], [1, 1]], [[3], [4], [2], [1]], etc. Cuando sea posible, [1, 1] y
    [1] se establecen en alturas específicas, mientras que [2], [3], [4], [5], etc.
    se permiten estirar para llenar el espacio.

    A partir de ahora, _group_double_1s tiene restringido intencionalmente la
    producción de cualquier agrupación (como [[1], [1, 1]]) que impida bloquear todos
    los individuales e dobles, preo creé esta función para manejar cualquier
    agrupación imaginable que _group_double_1s puede producir en el futuro.

    A partir de ahora, _group double_1s tiene restringido intencionalmente la
    producción de cualquier agrupación (como [[1], [1, 1]]) que impida bloquear todos
    los individuales y dobles, pero creé esta función para manejar cualquier
    agrupación imaginable que _group double_1s pueda producir en el futuro.

    Que _group_double_1s nunca hará (porque no se ha implementado nada para esto) es
    crear un grupo más largo que 2 o un grupo de dos con cualquier valor que no sea
    1.
    """
    if not groups:
        msg = "No groups to divvy in divvy_height."
        raise ValueError(msg)
    if locks is None:
        single_height = bbox.width / 2
        double_height = bbox.width
        locks = [([1, 1], double_height), ([1], single_height)]

    heights: list[float | None] = [None] * len(groups)

    def zip_hg() -> Iterator[tuple[float | None, list[int]]]:
        return zip(heights, groups, strict=True)

    for lock in locks:
        heights = [lock[1] if g == lock[0] else h for h, g in zip_hg()]

    if None not in heights:
        if not locks:
            msg = "Failed to find scalable groups in divvy_height."
            raise RuntimeError(msg)
        return _divvy_height(bbox, groups, locks=locks[:-1])

    free_height = bbox.height - sum(filter(None, heights))
    free_slices = [sum(g) for h, g in zip_hg() if h is None]
    scale = free_height / sum(free_slices)
    for i, height in enumerate(heights):
        heights[i] = height if height is not None else free_slices.pop(0) * scale

    if None in heights:
        msg = "Failed to fill bbox height in divvy_height."
        raise RuntimeError(msg)
    return list(filter(None, heights))


def position_blocks(bbox: su.BoundingBox, dist: list[int]) -> Iterator[su.BoundingBox]:
    """Yield una BoundingBox para cada bloque en la paleta."""
    groups = _group_double_1s(dist)
    heights = _divvy_height(bbox, groups)

    at_y = bbox.y
    for group, height in zip(groups, heights, strict=True):
        at_x = bbox.x
        for width in (bbox.width * g / len(group) for g in group):
            yield su.BoundingBox(at_x, at_y, width, height)
            at_x += width
        at_y += height


@dataclasses.dataclass
class ColorBlocks:
    """Todas información necesaria para crear los bloques de color.

    :param colors: una lista de colores hexadecimales
    :param heights: una lista de alturas *absolutas* para cada grupo de bloques de
        color
    :param groups: una lista de número de entradas de paleta en cada grupo
    :param args: a string of the input arguments (colors and dist) output by whatever
        created the palette.

    `heights` y `groups` deben tener la misma longitud.
    `colors` debe tener longitud == `sum(groups)`.

    Por ejemplo:

    colors: ["#ff0000", "#00ff00", "#0000ff"]
    heights: [10, 20]
    groups: [2, 1]

    Esta debería ser suficiente información para crear cualquier diseño de bloque de
    paleta de proyectos de paleta anteriores.
    """

    colors: list[str]
    heights: list[float]
    groups: list[int]
    input_args: str

    @property
    def names(self) -> list[str]:
        """Devuelve una lista de nombres de colores."""
        return get_colornames(*self.colors)

    @property
    def _bboxes(self) -> Iterator[su.BoundingBox]:
        """Genera una BoundingBox para cada bloque de color."""
        for i, group in enumerate(self.groups):
            top = geo.blocks_bbox.y + sum(self.heights[:i])
            bot = geo.blocks_bbox.y + sum(self.heights[: i + 1])
            row_bbox = su.cut_bbox(geo.blocks_bbox, y=top, y2=bot)
            if group == 1:
                yield row_bbox
                continue
            ts = [x / group for x in range(group + 1)]
            xs = [row_bbox.x + x * row_bbox.width for x in ts]
            for x, x2 in it.pairwise(xs):
                yield su.cut_bbox(row_bbox, x=x, x2=x2)

    @property
    def bboxes(self) -> Iterator[su.BoundingBox]:
        """Pad bboxes para restaurar el PALETTE_GAP."""
        for bbox in self._bboxes:
            yield su.pad_bbox(bbox, -geo.PALETTE_GAP / 2)


def _get_input_arg_string(colors: Iterable[str], dist: list[float] | None) -> str:
    """Crear una cadena de argumentos para la función de entrada."""
    colors = [color_to_hex(c)[1:] for c in colors]
    dist = dist or [1.0] * len(colors)
    if len(dist) != len(colors):
        msg = "Colors and dist must have the same length."
        raise ValueError(msg)
    return "|".join(it.chain(colors, map(str, dist)))


def classic_color_blocks_args(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> tuple[list[str], list[list[int]]]:
    """Crear los argumentos para ColorBlocks desde los argumentos de la función.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
        Aque, se ignora.
    :return: una tupla de dos listas: colors, groups
    """
    del dist
    colors = [color_to_hex(c) for c in colors]
    groups = [[1], [1], [1], [1], [1, 1]]
    return colors, groups


def classic_color_blocks(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> ColorBlocks:
    """Crear el diseño de bloques de color en mis paletas anteriores.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
        Aque, se ignora.
    :return: una instancia de ColorBlocks
    """
    colors, groups = classic_color_blocks_args(colors, dist)
    height = geo.blocks_bbox.height / 5
    return ColorBlocks(
        colors,
        [height] * 5,
        [len(x) for x in groups],
        _get_input_arg_string(colors, dist),
    )


def avant_garde_color_blocks_args(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> tuple[list[str], list[list[int]]]:
    """Crear los argumentos para ColorBlocks desde los argumentos de la función.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
        Aque, se ignora.
    :return: una tupla de dos listas: colors, groups

    Recurra al diseño *classic* si no hay un argumento dist o si todas las
    proporciones dist son iguales (después de distribuirlas en 12 unidades). Esto
    hace que [1, 1, 1, 1, 1, 1] tenga el mismo aspecto que [2, 2, 2, 2, 2, 2].
    """
    if dist is None:
        return classic_color_blocks_args(colors)
    discrete_dist = fit_partition_to_distribution(AVANT_GARDE_SLICES, dist)
    if discrete_dist.count(1) == 0:
        return classic_color_blocks_args(colors)
    colors = [color_to_hex(c) for c in colors]
    groups = _group_double_1s(discrete_dist)
    return colors, groups


def avant_garde_color_blocks(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> ColorBlocks:
    """Crear el diseño de bloques de color de mis paletas avant garde.

    Eston tienen un poco más de flexibilidad que los bloques clásicos. Los grupos de
    [1] o [1, 1] tiened alturas fijas. Todos los demás grupos pueden estirarse para
    llenar la altura del bbox.

    La `dist` se fuerza en 12 unidades discretas.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
    :return: una instancia de ColorBlocks
    """
    colors, groups = avant_garde_color_blocks_args(colors, dist)
    heights = _divvy_height(geo.blocks_bbox, groups)
    return ColorBlocks(
        colors, heights, [len(x) for x in groups], _get_input_arg_string(colors, dist)
    )


def _redistribute_slivers(dist: list[int]) -> list[int]:
    """Redistribuya *slivers* para que no estén en la puntos finales ni adyacentes.

    :param dist: una lista de enteros representando la altura relativa de cada bloque
    :return: una lista de enteros de modo que [dist[i] for i in return] es
        reorganizará dist para que no haya fragmentos adyacentes o en los puntos
        finales.
    """
    if dist[0] != 1 and dist[-1] != 1 and (1, 1) not in it.pairwise(dist):
        return list(range(len(dist)))

    def get_score(d: list[int]) -> int:
        """Puntuar una distribución de bloques."""
        reordered = (dist[x] for x in d)
        return max(sum(ab) for ab in it.pairwise(reordered))

    large = [i for i, x in enumerate(dist) if x > 1]
    small = [i for i, x in enumerate(dist) if x == 1]
    if len(small) >= len(large):
        msg = (
            f"Cannot distribute {len(small)} slivers among {len(large)}"
            + " blocks with none adjacent or at endpoints."
        )
        raise ValueError(msg)

    best_score = math.inf
    best_dist = list(range(len(dist)))

    for slots in it.combinations(range(1, len(large)), len(small)):
        candidate = large.copy()
        for i, slot in enumerate(reversed(slots)):
            candidate.insert(slot, small[-i])
        score = get_score(candidate)
        if score < best_score:
            best_score = score
            best_dist = candidate

    return best_dist


def sliver_color_blocks_args(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> tuple[list[str], list[list[int]]]:
    """Crear los argumentos para ColorBlocks desde los argumentos de la función.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
    :return: una tupla de dos listas: colors, groups
    """
    if dist is None:
        return classic_color_blocks_args(colors)
    discrete_dist = fit_partition_to_distribution_with_slivers(SLIVER_SLICES, dist)
    if min(discrete_dist) > 1:
        return avant_garde_color_blocks_args(colors, dist)
    colors = [color_to_hex(c) for c in colors]
    new_order = _redistribute_slivers(discrete_dist)
    colors = [colors[i] for i in new_order]
    discrete_dist = [discrete_dist[i] for i in new_order]
    groups = _group_double_1s(discrete_dist)
    return colors, groups


def sliver_color_blocks(
    colors: Iterable[str] | Iterable[tuple[float, float, float]],
    dist: list[float] | None = None,
) -> ColorBlocks:
    """Crear el diseño de bloques de color de mis paletas Alphonse Mucha.

    :param colors: una lista de colores hexadecimales o RGB
    :param dist: una lista de valores que definen la altura de cada fila de bloques.
    :return: una instancia de ColorBlocks

    Este es el más flexible porque distribuye los colores en 24 porciones discretas.
    Esto significa que los 1 son bastante delgados. Estos bloques delgados no se ven
    bien en los puntos finales o adyacentes entre sí, por lo que se mueven (y los
    colores con ellos) para evitar estas situaciones. Eso significa que esta función
    podría reordenar los colores.
    """
    colors, groups = sliver_color_blocks_args(colors, dist)
    if sum(map(sum, groups)) < SLIVER_SLICES:
        # se utilizó otro tipo de diseño
        locks = None
    else:
        locks = [([1], geo.blocks_bbox.width / 4)]
    heights = _divvy_height(geo.blocks_bbox, groups, locks=locks)
    return ColorBlocks(
        colors, heights, [len(x) for x in groups], _get_input_arg_string(colors, dist)
    )
