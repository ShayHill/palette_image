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

from collections.abc import Iterator, Sequence

import svg_ultralight as su


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
