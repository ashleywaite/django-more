from django.db import models


class NullCharField(models.CharField):
    """ CharField that stores blanks as NULL """
    def __init__(self, *args, null=True, blank=True, **kwargs):
        if not null or not blank:
            raise ValueError('NullCharField cannot have null or blank settings turned off')

        super().__init__(*args, null=null, blank=blank, **kwargs)

    def pre_save(self, instance, add):
        value = super().pre_save(instance, add)
        if value in self.empty_values:
            setattr(instance, self.attname, None)
            return None
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        return value
