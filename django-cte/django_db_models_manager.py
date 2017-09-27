

class BaseManager:
    def attach(self, *args, **kwargs):
        # Proxy through an all() call as this is implied with attaching
        return self.get_queryset().attach(*args, **kwargs)
