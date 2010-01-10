"""
>>> from django.utils.tzinfo import FixedOffset

>>> FixedOffset(0)
+0000
>>> FixedOffset(60)
+0100
>>> FixedOffset(-60)
-0100
>>> FixedOffset(280)
+0440
>>> FixedOffset(-280)
-0440
>>> FixedOffset(-78.4)
-0118
>>> FixedOffset(78.4)
+0118
>>> FixedOffset(-5.5*60)
-0530
>>> FixedOffset(5.5*60)
+0530
>>> FixedOffset(-.5*60)
-0030
>>> FixedOffset(.5*60)
+0030
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
