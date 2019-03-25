"""Defines a multi-dimensional array and useful procedures for Numerical computation.

Functions

-   array                      - NumPy Array construction
-   zeros                      - Return an array of all zeros
-   empty                      - Return an uninitialized array
-   shape                      - Return shape of sequence or array
-   rank                       - Return number of dimensions
-   size                       - Return number of elements in entire array or a
                                 certain dimension
-   fromstring                 - Construct array from (byte) string
-   take                       - Select sub-arrays using sequence of indices
-   put                        - Set sub-arrays using sequence of 1-D indices
-   putmask                    - Set portion of arrays using a mask
-   reshape                    - Return array with new shape
-   repeat                     - Repeat elements of array
-   choose                     - Construct new array from indexed array tuple
-   correlate                  - Correlate two 1-d arrays
-   searchsorted               - Search for element in 1-d array
-   sum                        - Total sum over a specified dimension
-   average                    - Average, possibly weighted, over axis or array.
-   cumsum                     - Cumulative sum over a specified dimension
-   product                    - Total product over a specified dimension
-   cumproduct                 - Cumulative product over a specified dimension
-   alltrue                    - Logical and over an entire axis
-   sometrue                   - Logical or over an entire axis
-   allclose                   - Tests if sequences are essentially equal

More Functions:

-   arange                     - Return regularly spaced array
-   asarray                    - Guarantee NumPy array
-   convolve                   - Convolve two 1-d arrays
-   swapaxes                   - Exchange axes
-   concatenate                - Join arrays together
-   transpose                  - Permute axes
-   sort                       - Sort elements of array
-   argsort                    - Indices of sorted array
-   argmax                     - Index of largest value
-   argmin                     - Index of smallest value
-   inner                      - Innerproduct of two arrays
-   dot                        - Dot product (matrix multiplication)
-   outer                      - Outerproduct of two arrays
-   resize                     - Return array with arbitrary new shape
-   indices                    - Tuple of indices
-   fromfunction               - Construct array from universal function
-   diagonal                   - Return diagonal array
-   trace                      - Trace of array
-   dump                       - Dump array to file object (pickle)
-   dumps                      - Return pickled string representing data
-   load                       - Return array stored in file object
-   loads                      - Return array from pickled string
-   ravel                      - Return array as 1-D
-   nonzero                    - Indices of nonzero elements for 1-D array
-   shape                      - Shape of array
-   where                      - Construct array from binary result
-   compress                   - Elements of array where condition is true
-   clip                       - Clip array between two values
-   ones                       - Array of all ones
-   identity                   - 2-D identity array (matrix)

(Universal) Math Functions

       add                    logical_or             exp
       subtract               logical_xor            log
       multiply               logical_not            log10
       divide                 maximum                sin
       divide_safe            minimum                sinh
       conjugate              bitwise_and            sqrt
       power                  bitwise_or             tan
       absolute               bitwise_xor            tanh
       negative               invert                 ceil
       greater                left_shift             fabs
       greater_equal          right_shift            floor
       less                   arccos                 arctan2
       less_equal             arcsin                 fmod
       equal                  arctan                 hypot
       not_equal              cos                    around
       logical_and            cosh                   sign
       arccosh                arcsinh                arctanh

"""
from __future__ import division, absolute_import, print_function

depends = ['testing']
global_symbols = ['*']
