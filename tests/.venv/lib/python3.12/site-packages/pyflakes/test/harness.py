import ast
import textwrap
import unittest

from pyflakes import checker

__all__ = ["TestCase", "skip", "skipIf"]

skip = unittest.skip
skipIf = unittest.skipIf


class TestCase(unittest.TestCase):

    withDoctest = False

    def flakes(self, input, *expectedOutputs, **kw):
        tree = ast.parse(textwrap.dedent(input))
        if kw.get("is_segment"):
            tree = tree.body[0]
            kw.pop("is_segment")
        w = checker.Checker(tree, withDoctest=self.withDoctest, **kw)
        outputs = [type(o) for o in w.messages]
        expectedOutputs = list(expectedOutputs)
        outputs.sort(key=lambda t: t.__name__)
        expectedOutputs.sort(key=lambda t: t.__name__)
        self.assertEqual(
            outputs,
            expectedOutputs,
            """\
for input:
{}
expected outputs:
{!r}
but got:
{}""".format(
                input, expectedOutputs, "\n".join([str(o) for o in w.messages])
            ),
        )
        return w
