"""Type hints interno de Python que no están disponibles en módulos públicos.

:author: Shay Hill
:created: 2024-12-27
"""

from typing import Any, Protocol, TypeAlias, TypeVar

_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsDunderLT(Protocol[_T_contra]):
    """Protocolo para objetos que soportan el operador de comparación "<"."""

    def __lt__(self, other: _T_contra, /) -> bool:
        """Devolver si self es menor que other."""
        ...


class SupportsDunderGT(Protocol[_T_contra]):
    """Protocolo para objetos que soportan el operador de comparación ">"."""

    def __gt__(self, other: _T_contra, /) -> bool:
        """Devolver si self es mayor que other."""
        ...


# Toda la clasificación se realiza con __lt__ en Python, pero a *pyright* no le
# gusta. LT y GT son necesarios para tipos integrados como int y float para que
# coincidan con SupportsRichComparison.
SupportsRichComparison: TypeAlias = SupportsDunderLT[Any] | SupportsDunderGT[Any]
SupportsRichComparisonT = TypeVar(
    "SupportsRichComparisonT", bound=SupportsRichComparison
)
