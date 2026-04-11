import numpy as np
import numpy.typing as npt

AR_i: npt.NDArray[np.int64]
AR_f: npt.NDArray[np.float64]
AR_c: npt.NDArray[np.complex128]
AR_m: npt.NDArray[np.timedelta64]
AR_M: npt.NDArray[np.datetime64]

AR_f > AR_m  # type: ignore[operator]
AR_c > AR_m  # type: ignore[operator]

AR_m > AR_f  # type: ignore[operator]
AR_m > AR_c  # type: ignore[operator]

AR_i > AR_M  # type: ignore[operator]
AR_f > AR_M  # type: ignore[operator]
AR_m > AR_M  # type: ignore[operator]

AR_M > AR_i  # type: ignore[operator]
AR_M > AR_f  # type: ignore[operator]
AR_M > AR_m  # type: ignore[operator]

AR_i > ""  # type: ignore[operator]
AR_i > b""  # type: ignore[operator]
"" > AR_M  # type: ignore[operator]
b"" > AR_M  # type: ignore[operator]
