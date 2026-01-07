from . import py36, py37, py38, py39, py310, py311, py312, py313, py314

stdlib = (
    py36.stdlib
    | py37.stdlib
    | py38.stdlib
    | py39.stdlib
    | py310.stdlib
    | py311.stdlib
    | py312.stdlib
    | py313.stdlib
    | py314.stdlib
)
