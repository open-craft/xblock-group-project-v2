from group_project_v2.utils import gettext as _

# Generic messages
UNKNOWN_ERROR = _(u"Unknown error.")
COMPONENT_MISCONFIGURED = _(
    u"This component is misconfigured and can't be displayed. It needs to be fixed by the course authors."
)
STAGE_NOT_OPEN_TEMPLATE = _(u"Can't {action} as stage is not yet opened.")
STAGE_CLOSED_TEMPLATE = _(u"Can't {action} as stage is closed.")

# Group Project XBlock messages
NO_ACTIVITIES = _(u"This Group Project does not contain any activities.")
NO_PROJECT_NAVIGATOR = _(
    u"This Group Project V2 does not contain Project Navigator - please edit course outline "
    u"in Studio to include one."
)
NO_DISCUSSION = _(u"This Group Project V2 does not contain a discussion.")
MUST_CONTAIN_PROJECT_NAVIGATOR_BLOCK = _(u"Group Project must contain Project Navigator Block.")

# Group Activity XBlock messages
NO_STAGES = _(u"This Group Project Activity does not contain any stages.")
SHOULD_BE_INTEGER = _(u"{field_name} must be integer, {field_value} given.")
ASSIGNED_TO_GROUPS_LABEL = _(u"This project is assigned to {group_count} group(s)")  # no full stop (period) by design

# Project Navigator messages
MUST_CONTAIN_NAVIGATION_VIEW = _(u"Project Navigator must contain Navigation view.")
NO_DISCUSSION_IN_GROUP_PROJECT = _(
    u"Parent group project does not contain discussion XBlock - this {block_type} "
    u"will not function properly and will not be displayed to students."
)

# Stages messages
STAGE_COMPLETION_MESSAGE = _(u"This task has been marked as complete.")
STAGE_URL_NAME_TEMPLATE = _(u"url_name to link to this {stage_name}:")
SUBMISSIONS_BLOCKS_ARE_MISSING = _(u"Submissions are not specified for {class_name} '{stage_title}'.")
FEEDBACK_BLOCKS_ARE_MISSING = _(u"Feedback display blocks are not specified for {class_name} '{stage_title}'.")
QUESTION_BLOCKS_ARE_MISSING = _(u"Questions are not specified for {class_name} '{stage_title}'.")
PEER_SELECTOR_BLOCK_IS_MISSING = _(
    u"{class_name} stage '{stage_title}' is missing required component '{peer_selector_class_name}'."
)
GROUP_SELECTOR_BLOCK_IS_MISSING = _(
    u"{class_name} stage '{stage_title}' is missing required component '{group_selector_class_name}'."
)
FEEDBACK_SAVED_MESSAGE = _(u'Thanks for your feedback.')
TA_GRADING_NOT_ALLOWED = _(u"TA grading is not allowed for this stage.")
GRADED_QUESTIONS_NOT_SUPPORTED = _(u"Graded questions are not supported for {class_name} stage '{stage_title}'.")
GRADED_QUESTIONS_ARE_REQUIRED = _(u"Grade questions are required for {class_name} stage '{stage_title}'.")

# Stage component messages
MUST_CONTAIN_CONTENT_ID = _(u"Video Resource Block must contain Ooyala content ID.")
NON_GROUP_MEMBER_UPLOAD = _(u"Only group members can upload files.")
QUESTION_NOT_SELECTED = _(u"Question is not selected.")
SUCCESSFUL_UPLOAD_TITLE = _(u"Upload complete")  # no full stop (period) by design
FAILED_UPLOAD_TITLE = _(u"Upload failed.")
SUCCESSFUL_UPLOAD_MESSAGE_TPL = _(
    u"Your deliverable has been successfully uploaded. You can attach an updated version of the "
    u"deliverable by clicking the <span class='icon {icon}'></span> icon at any time before the deadline."
)
FAILED_UPLOAD_MESSAGE_TPL = _(u"Error uploading file: {error_goes_here}.")
