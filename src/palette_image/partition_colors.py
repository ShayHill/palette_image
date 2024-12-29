"""Convertir una distribución continua de colores en una partition discreta.

La imagen de la paleta de bloques de color tiene alguna flexibilidad para mostrar los
pesos relativos de los colores. Para hacer esto, se dividen en rebanadas y a cada
color se asigna un número de esas rebanadas (mínimo 1).

:author: Shay Hill
:created: 2024-11-30
"""

from __future__ import annotations

from operator import itemgetter
from typing import TYPE_CHECKING

from restricted_partition import iter_partition

from palette_image.type_hints import SupportsRichComparisonT

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


def _get_chi_squared(
    hypothesis: Sequence[float] | Sequence[int],
    observation: Sequence[float] | Sequence[int],
) -> float:
    """Devolver el error entre dos listas de números de la misma longitud.

    :param hypothesis: la lista de números que se consideran la verdad
    :param observation: la lista de números que se consideran la observación
    :return: el error cuadrado medio entre las dos listas

    Aqui, esto se usa para encontrar la mejor distribución de "slices" discretos
    (observation) para aproximar la distribución continua (hypothesis) de los tamaños
    reales de los *clusters* de colores.

    Los *distributions* no necesitan sumar a 1. Cada *partition* (observation) sumará
    la misma cantidad, por lo que probarlos todas por ajustarse a la misma hypothesis
    será simplemente ordenarlos por un ajuste escalado uniformemente.
    """
    if len(hypothesis) != len(observation):
        msg = f"{len(hypothesis)=} != {len(observation)=}"
        raise ValueError(msg)
    if 0 in hypothesis:
        msg = f"{hypothesis=} cannot contain 0"
        raise ValueError(msg)
    return sum(
        (obs - hyp) ** 2 / hyp for obs, hyp in zip(observation, hypothesis, strict=True)
    )


def _sort_retain_order(
    items: list[SupportsRichComparisonT],
) -> tuple[list[SupportsRichComparisonT], list[int]]:
    """Ordenar elementos, pero conservar el orden original de los elementos.

    :param items: los elementos a ordenar
    :return: una tupla con los elementos ordenados y una lista de índices para
        devolver los elementos ordenados a su orden original.

    sorted, indices = _sort_retain_order(items)
    [sorted[i] for i in indices] == items
    """
    orig_idx = [i for i, _ in sorted(enumerate(items), key=itemgetter(1))]
    dest_idx = [j for j, _ in sorted(enumerate(orig_idx), key=itemgetter(1))]
    return [items[i] for i in orig_idx], dest_idx


def _get_restricted_partition_without_zeros(
    num_items: int, num_groups: int
) -> Iterator[list[int]]:
    """Devolver todas las *partitions* de num_items en num_groups SIN CEROS.

    :param num_items: número de elementos a *partition*
    :param num_groups: número de grupos en los que *partition*
    :yield: *partitions* de num_items en num_groups sin ceros

    `iter_partitions(num_items, num_groups)` producirá *partitions* con ceros. Por
    ejemplo, para 3 elementos y 2 grupos, producirá [1, 2] y [3]. Aquí, el [3] es
    [0, 3], lo cual no es lo que queremos, porque una paleta de dos colores con una
    entrada que pesa 0 es, de hecho, una palete de un solo color. Esta función filtra
    las *partitions* con ceros.
    """
    all_partitions = iter_partition(num_items, num_groups)
    return (x for x in all_partitions if len(x) == num_groups)


def _score_partitions_by_fit(
    items: int, goal_dist: list[float]
) -> Iterator[tuple[float, list[int]]]:
    """Yield particiones de longitud goal_dist de items, puntuado por chi-squared.

    :param items: el número entero que se va a *partition*
    :param goal_dist: la distribución objetivo (p relativo para cada elemento).
        No necesita sumar a 1.
    :yield: una tupla con el ajuste chi-squared y la *partition*
    """
    sorted_dist, sort_order = _sort_retain_order(goal_dist)

    def fit(partition: list[int]) -> float:
        """Que tan cerca se ajusta la partition a la distribution objetivo."""
        return _get_chi_squared(sorted_dist, partition)

    for ps in _get_restricted_partition_without_zeros(items, len(goal_dist)):
        yield fit(ps), [ps[i] for i in sort_order]


def fit_partition_to_distribution(items: int, goal_dist: list[float]) -> list[int]:
    """Partition un entero para ajustarse a goal_dist lo más cerca posible.

    :param items: el número entero que se va a *partition*
    :param goal_dist: la distribución objetivo (p relativo para cada elemento).
        No necesita sumar a 1.
    :return: items partitioned into len(goal_dist) slots, portioned as closely as
        possible to goal_dist.

    fit_partition_to_distribution(3, [2/3, 1/3]) -> [2, 1]
    fit_partition_to_distribution(3, [1/3, 2/3]) -> [1, 2]
    fit_partition_to_distribution(10, [2/3, 1/3]) -> [7, 3]
    """
    return min(_score_partitions_by_fit(items, goal_dist), key=itemgetter(0))[1]


def fit_partition_to_distribution_with_slivers(
    items: int, goal_dist: list[float]
) -> list[int]:
    """Partition un entero para ajustarse a goal_dist lo más cerca posible.

    :param items: el número entero que se va a *partition*
    :param goal_dist: la distribución objetivo (p relativo para cada elemento).
        No necesita sumar a 1.
    :return: items partitioned into len(goal_dist) slots, portioned as closely as
        possible to goal_dist.

    Esta versión permite *slivers* de 1. Los arreglos de bloques de colores como los
    de Alphonse Mucha usan un valor alto (24) de *items* y un altura fija delgado para
    1s.  Esto representa 1s como *slivers* de 1/24 de altura de la altura total. Para
    mejorar la estética, el código posterior a esta función moverá estas *slivers*
    para que no estén en la parte superior o inferior (donde se ven mal con las
    curvas) o adyacentes entre sí. La restricción aquí es que no puede haber más de 2
    *slivers* en una paleta de 6 colores, de lo contrario esta reorganización no
    sería posible.

    Si no hay 1s en la mejor partición y items//2 >= len(goal dist), entonces haga
    más gruesa la partición para que parezca menos *continua*.
    """
    max_1s = (len(goal_dist) + 1) // 2 - 1
    ps = min(_score_partitions_by_fit(items, goal_dist), key=itemgetter(0))[1]
    if ps.count(1) <= max_1s:
        return ps
    return fit_partition_to_distribution(items // 2, goal_dist)
