import unittest
import uuid
from typing import Callable

from versatile.registry import provides





class MyTestCase(unittest.TestCase):
    def test_something(self):
        context = str(uuid.uuid4())

        @provides(context=context)
        def build_greeter() -> Callable:
            def greeter():
                return 'Hello, world!'

            return greeter

        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
