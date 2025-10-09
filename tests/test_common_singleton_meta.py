import unittest

from robot_hat.common.singleton_meta import SingletonMeta


class TestSingletonMeta(unittest.TestCase):
    def test_singleton_behavior(self):
        """Test that classes using SingletonMeta return the same instance."""

        class TestSingleton(metaclass=SingletonMeta):
            def __init__(self, value=0):
                self.value = value

        instance1 = TestSingleton(10)
        instance2 = TestSingleton(20)

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.value, 10)

    def test_multiple_singleton_classes(self):
        """Test that different singleton classes have separate instances."""

        class Singleton1(metaclass=SingletonMeta):
            def __init__(self):
                self.name = "Singleton1"

        class Singleton2(metaclass=SingletonMeta):
            def __init__(self):
                self.name = "Singleton2"

        instance1 = Singleton1()
        instance2 = Singleton2()

        self.assertIsNot(instance1, instance2)
        self.assertEqual(instance1.name, "Singleton1")
        self.assertEqual(instance2.name, "Singleton2")

    def test_singleton_with_arguments(self):
        """Test singleton behavior with constructor arguments."""

        class ConfigurableSingleton(metaclass=SingletonMeta):
            def __init__(self, config_value="default"):
                self.config = config_value

        instance1 = ConfigurableSingleton("first")

        instance2 = ConfigurableSingleton("second")

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.config, "first")

    def test_singleton_with_keyword_arguments(self):
        """Test singleton behavior with keyword arguments."""

        class KWArgsSingleton(metaclass=SingletonMeta):
            def __init__(self, name="default", value=0):
                self.name = name
                self.value = value

        instance1 = KWArgsSingleton(name="test", value=42)
        instance2 = KWArgsSingleton(name="other", value=99)

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.name, "test")
        self.assertEqual(instance1.value, 42)

    def test_singleton_inheritance(self):
        """Test that singleton behavior works with inheritance."""

        class BaseSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.base_value = "base"

        class DerivedSingleton(BaseSingleton):
            def __init__(self):
                super().__init__()
                self.derived_value = "derived"

        instance1 = DerivedSingleton()
        instance2 = DerivedSingleton()

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.base_value, "base")
        self.assertEqual(instance1.derived_value, "derived")

    def test_singleton_with_abc(self):
        """Test that SingletonMeta works with ABC."""
        from abc import ABC, abstractmethod

        class AbstractSingleton(ABC, metaclass=SingletonMeta):
            @abstractmethod
            def abstract_method(self):
                pass

        class ConcreteSingleton(AbstractSingleton):
            def abstract_method(self):  # type: ignore
                return "implemented"

        instance1 = ConcreteSingleton()
        instance2 = ConcreteSingleton()

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.abstract_method(), "implemented")

    def test_singleton_instances_storage(self):
        """Test that singleton instances are stored in the metaclass."""

        class TestSingleton(metaclass=SingletonMeta):
            pass

        instance = TestSingleton()

        self.assertIn(TestSingleton, SingletonMeta._instances)
        self.assertIs(SingletonMeta._instances[TestSingleton], instance)

    def test_multiple_instantiation_ignores_args(self):
        """Test that multiple instantiations with different args are ignored."""

        class ArgsSingleton(metaclass=SingletonMeta):
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        instance1 = ArgsSingleton(1, 2, 3, a=1, b=2)

        instance2 = ArgsSingleton(4, 5, 6, c=3, d=4)

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.args, (1, 2, 3))
        self.assertEqual(instance1.kwargs, {"a": 1, "b": 2})

    def test_singleton_type_annotation(self):
        """Test that singleton instances maintain proper type annotations."""

        class TypedSingleton(metaclass=SingletonMeta):
            def __init__(self, value: int = 0):
                self.value: int = value

        instance1 = TypedSingleton(42)
        instance2 = TypedSingleton(84)

        self.assertIs(instance1, instance2)
        self.assertIsInstance(instance1.value, int)
        self.assertEqual(instance1.value, 42)


if __name__ == "__main__":
    unittest.main()
