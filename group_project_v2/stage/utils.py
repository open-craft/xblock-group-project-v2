from group_project_v2.utils import _


class StageState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'

    HUMAN_NAMES_MAP = {
        NOT_STARTED: _("Not started"),
        INCOMPLETE: _("Partially complete"),
        COMPLETED: _("Complete")
    }

    @classmethod
    def get_human_name(cls, state):
        return cls.HUMAN_NAMES_MAP.get(state)


class ReviewState(object):
    NOT_STARTED = 'not_started'
    INCOMPLETE = 'incomplete'
    COMPLETED = 'completed'


DISPLAY_NAME_NAME = _(u"Display Name")
DISPLAY_NAME_HELP = _(U"This is a name of the stage")
