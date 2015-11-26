from xblock.fields import Boolean, Scope
from group_project_v2.utils import gettext as _
from group_project_v2.stage.utils import StageState


class SimpleCompletionStageMixin(object):
    """
    runtime.publish(block, 'progress', {'user_id': user_id}) properly creates completion records, but they are
    unavailable to API until current request is ended. They are created in transaction and looks like in LMS every
    request have dedicated transaction, but that's speculation. Anyway, we can't rely on
    runtime.publish - project_api.get_stage_id to update stage state and get new state in single run.
    """
    completed = Boolean(
        display_name=_(u"Completed"),
        scope=Scope.user_state
    )

    def get_stage_state(self):
        if self.completed:
            return StageState.COMPLETED
        return StageState.NOT_STARTED

    def mark_complete(self, user_id=None):
        result = super(SimpleCompletionStageMixin, self).mark_complete(user_id)
        self.completed = True
        return result

    def get_users_completion(self, target_workgroups, target_users):
        """
        Returns sets of completed user ids and partially completed user ids
        :param collections.Iterable[group_project_v2.project_api.dtos.WorkgroupDetails] target_workgroups:
        :param collections.Iterable[group_project_v2.project_api.dtos.ReducedUserDetails] target_users:
        :rtype: (set[int], set[int])
        """
        completions = self.project_api.get_completions_by_content_id(self.course_id, self.content_id)
        return set(completion.user_id for completion in completions), set()
