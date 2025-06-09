import unittest
import uuid
from typing import Callable

from versatile.registry import provides, components_registered_in


class MyTestCase(unittest.TestCase):
    def test_something(self):
        context = str(uuid.uuid4())

        @provides(name='greeter', context=context)
        def build_greeter() -> Callable:
            def greeter():
                return 'Hello, world!'

            return greeter

        self.assertEqual('greeter', components_registered_in(context)[0].name)


if __name__ == '__main__':
    unittest.main()
