import pytest

import numpy as np
from numpy import exp2, log10
from numpy._core import numerictypes as ntypes


class MachArLike:
    """Minimal class to simulate machine arithmetic parameters."""
    def __init__(self, dtype, machep, negep, minexp, maxexp, nmant, iexp):
        self.dtype = dtype
        self.machep = machep
        self.negep = negep
        self.minexp = minexp
        self.maxexp = maxexp
        self.nmant = nmant
        self.iexp = iexp
        self.eps = exp2(dtype(-nmant))
        self.epsneg = exp2(dtype(negep))
        self.precision = int(-log10(self.eps))
        self.resolution = dtype(10) ** (-self.precision)


@pytest.fixture
def float16_ma():
    """Machine arithmetic parameters for float16."""
    f16 = ntypes.float16
    return MachArLike(f16,
                      machep=-10,
                      negep=-11,
                      minexp=-14,
                      maxexp=16,
                      nmant=10,
                      iexp=5)


@pytest.fixture
def float32_ma():
    """Machine arithmetic parameters for float32."""
    f32 = ntypes.float32
    return MachArLike(f32,
                      machep=-23,
                      negep=-24,
                      minexp=-126,
                      maxexp=128,
                      nmant=23,
                      iexp=8)


@pytest.fixture
def float64_ma():
    """Machine arithmetic parameters for float64."""
    f64 = ntypes.float64
    return MachArLike(f64,
                      machep=-52,
                      negep=-53,
                      minexp=-1022,
                      maxexp=1024,
                      nmant=52,
                      iexp=11)


@pytest.mark.parametrize("dtype,ma_fixture", [
    (np.half, "float16_ma"),
    (np.float32, "float32_ma"),
    (np.float64, "float64_ma"),
])
@pytest.mark.parametrize("prop", [
    'machep', 'negep', 'minexp', 'maxexp', 'nmant', 'iexp',
    'eps', 'epsneg', 'precision', 'resolution'
])
@pytest.mark.thread_unsafe(
    reason="complex fixture setup is thread-unsafe (pytest-dev/pytest#13768.)"
)
def test_finfo_properties(dtype, ma_fixture, prop, request):
    """Test that finfo properties match expected machine arithmetic values."""
    ma = request.getfixturevalue(ma_fixture)
    finfo = np.finfo(dtype)

    actual = getattr(finfo, prop)
    expected = getattr(ma, prop)

    assert actual == expected, (
        f"finfo({dtype}) property '{prop}' mismatch: "
        f"expected {expected}, got {actual}"
    )
