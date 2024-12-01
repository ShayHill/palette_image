"""Convertir una distribución continua de colores en una partition discreta.

The palette image color blocks have *some* flexibility to show the relative weights
of the colors. To do this, they are partitioned into slices, and each color is
assigned a number of those slices (minimum 1).

La imagen de la paleta de bloques de color tiene alguna flexibilidad para mostrar los
pesos relativos de los colores. Para hacer esto, se dividen en rebanadas y a cada
color se asigna un número de esas rebanadas (mínimo 1).

:author: Shay Hill
:created: 2024-11-30
"""

from collections.abc import Sequence

from restricted_partition import iter_partition
from typing import Sequence

from typing import Iterator, Protocol, TypeVar

_T = TypeVar("_T")


class _WithLessThan(Protocol):
    def __eq__(self: _T, __other: _T) -> bool: ...


_SortableT = TypeVar("_SortableT", bound=_WithLessThan)


def _get_chi_squared(hypothesis: Sequence[float], observation: Sequence[float]):
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
    return sum((obs - hyp) ** 2 / hyp for obs, hyp in zip(observation, hypothesis))


def _sort_retain_order(items: list[_SortableT]) -> tuple[list[_SortableT], list[int]]:
    """Ordenar elementos, pero conservar el orden original de los elementos.

    :param items: los elementos a ordenar
    :return: una tupla con los elementos ordenados y una lista de índices que
        representan la permutación de los elementos originales
    """
    items = list(items)
    order = list(range(len(items)))
    order.sort(key=lambda i: items[i])  # type: ignore
    return [items[i] for i in order], order


def _get_restricted_partition(num_items: int, num_groups: int) -> Iterator[list[int]]:
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
    sorted_dist, sort_order = _sort_retain_order(goal_dist)

    def fit(partition: list[int]) -> float:
        """Que tan cerca se ajusta la partition a la distribution objetivo."""
        return _get_chi_squared(sorted_dist, list(map(float, partition)))

    parts = _get_restricted_partition(items, len(goal_dist))
    best_fit = sorted(parts, key=fit)[0]
    return [best_fit[i] for i in sort_order]
