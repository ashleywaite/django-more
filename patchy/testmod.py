from . import super_patchy

STR_ORI = 'Original string'
STR_REP = 'Replaced string'
STR_ADD = 'Added string'
STR_OVR = 'Override string'
STR_INH = 'Inherited string'


class OriginalBase:
    def get_string(self):
        return STR_INH

    def get_strings(self, *strings):
        # Ignores params!
        return [self.get_string()]

    def get_inherited_string(self):
        return STR_INH

    @classmethod
    def get_inherited_class_strings(cls, *strings):
        return [STR_INH, cls.__name__] + list(strings) if strings is not None else []

    @staticmethod
    def get_inherited_static_strings(*strings):
        return [STR_INH] + list(strings) if strings is not None else []


class Original(OriginalBase):
    _string = STR_ORI

    def get_string(self):
        return self.string

    def get_strings(self, *strings):
        return super().get_strings(*strings) + list(strings) if strings is not None else []

    @property
    def string(self):
        return self._string

    @classmethod
    def get_class_strings(cls, *strings):
        return [STR_ORI, cls.__name__] + list(strings) if strings is not None else []

    @staticmethod
    def get_static_strings(*strings):
        return [STR_ORI] + list(strings) if strings is not None else []


class OriginalSlots(Original):
    # Makes inherited _string unavailable, must be set on instance
    __slots__ = ['_string']

    def get_slots_strings(self, *strings):
        return self.get_strings(*strings)


class OriginalGetAttribute(Original):
    def __getattribute__(self, attr):
        return [STR_ORI, attr]


class SimpleThings:
    def get_string(self):
        return STR_REP

    def get_inherited_string(self):
        return STR_REP

    def get_slots_strings(self, *strings):
        return [STR_REP] + list(strings) if strings is not None else []

    @property
    def string(self):
        return STR_REP

    @classmethod
    def get_class_strings(cls, *strings):
        return [STR_REP, cls.__name__] + list(strings) if strings is not None else []

    @staticmethod
    def get_static_strings(*strings):
        return [STR_REP] + list(strings) if strings is not None else []

    @classmethod
    def get_inherited_class_strings(cls, *strings):
        return [STR_REP, cls.__name__] + list(strings) if strings is not None else []

    @staticmethod
    def get_inherited_static_strings(*strings):
        return [STR_REP] + list(strings) if strings is not None else []


class SuperPatchyThings:
    def get_strings(self, *strings):
        return [STR_ADD] + super_patchy(*strings)


class SuperThings:
    def get_strings(self, *strings):
        # Bare super is not allowed!
        return [STR_ADD] + super(self.__class__, self).get_strings(*strings)
