"""
This package contains classes that parse Group project XML into a tree of domain-specific objects.
Basically it looks like the following

GroupActivity (.)
- GroupActivityStage (./activitystage)
-- GroupActivityQuestion (./activitystage/question)
--- <no dedicated class, etree.Element is used> (./activitystage/question/answer)
-- GroupActivityAssessment (./activitystage/assessment)
--- <no dedicated class, etree.Element is used> (./activitystage/assessment/answer)

GroupActivity (paths relative to root element)
- resources: [DottableDict(title, description, location)] - ./resources/document
# attribute filter implicit
- grading_criteria: [DottableDict(title, description, location)] - ./resources/document[@grading_criteria="true"]
- submissions: [DottableDict(id, title, description, location?)] - ./submissions/document
- grade_questions: [GroupActivityQuestion] - ./activitystage/question
- activity_stages: [GroupActivityStage] - ./activitystage
- grading_override: Bool                            # if True - allows visiting stages after close date; used by TA
* has_submissions: Bool                             # True if ANY submission uploaded
* has_all_submissions: Bool                         # True if ALL submissions uploaded
* step_map: json
    {
        <stage_id>: { prev: prev_stage.id, name: stage.name, next: next_stage.id},
        ordered_list: [stage1.id, stage2.id, ...],
        default: <latest_open_stage.id if not grading_override else latest_stage_with_group_review_stage.id>
    }

GroupActivityStage (paths relative to ./activitystage)
-- id: str - ./@id
-- title: str - ./@title
-- type: str - ./@type                                      # governs stage behavior
-- content: etree.Element - ./content                       # HTML
-- open_date: datetime.date - ./@open
-- close_date: datetime.date - ./@close
-- activity: GroupActivity                                  # parent link
** questions: [ActivityQuestion] - ./question
** assessments: [ActivityAssessment] - ./assessment
** resources: [DottableDict(title, description, location, grading_criteria)] - ./submissions/resource
** submissions: [DottableDict(id, title, description, location?)] - ./submissions/document
** is_upload_available: Bool                                # Is upload stage and opened and not closed

GroupActivityQuestion (paths relative to //section/question)
---- id: str - ./@id
---- label: etree.Element - ./label
---- stage: GroupActivityStage                               # parent reference
---- answer: etree.Element - ./answer[0]                     # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                        # affects "answer" presentation - adds "side" class
---- required: Bool - ./@required                            # affects "question" presentation - adds "required" class
---- designer_class: [str] - ./@class                        # affects "question" presentation - added as is
---- question_classes: [str]                                 # ['question', designer_class?, "required"?]

GroupActivityAssessment (paths relative to //section/assessment)
---- id: str - ./@id
---- label: etree.Element ./label
---- answer: etree.Element = ./answer[0]                     # should contain single HTML input control
---- small: Bool - ./answer[0]/@small                        # affects "answer" presentation - adds "side" class
"""
from activity import GroupActivity
from stage import (
    BasicStage, SubmissionStage, PeerReviewStage, GroupReviewStage, PeerAssessmentStage, GroupAssessmentStage,
    StageType
)
from review import GroupActivityQuestion, GroupActivityAssessment
