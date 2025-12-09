import threading


class SingletonBase:
    _instances = {}
    _locks = {}

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use 'Instance()' to get the Singleton instance")

    @classmethod
    def Instance(cls, *args, **kwargs):
        if cls not in cls._instances:
            # Ensure each derived class has its own lock
            if cls not in cls._locks:
                cls._locks[cls] = threading.Lock()
            with cls._locks[cls]:
                if cls not in cls._instances:
                    # Use object.__new__ to avoid calling cls.__new__ and triggering RuntimeError
                    instance = object.__new__(cls)
                    # Optional: check if __init_once__ exists (for robustness)
                    if hasattr(instance, "__init_once__"):
                        instance.__init_once__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    def __init_once__(self, *args, **kwargs):
        """Called only once per class instance. Override in derived class."""
        pass
