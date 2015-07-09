import copy
from lazy.lazy import lazy
import logging
import xml.etree.ElementTree as ET

from xblock.core import XBlock
from xblock.fields import String, UNIQUE_ID, Boolean
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin

from group_project_v2.utils import outer_html, inner_html, gettext as _
from group_project_v2.utils import loader


log = logging.getLogger(__name__)


class GroupProjectReviewQuestionXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-review-question"

    display_name_with_default = _(u"Review Question")

    question_id = String(
        display_name=_(u"Question ID"),
        default=UNIQUE_ID
    )

    # Label could be an HTML child XBlock, content could be a XBlock encapsulating HTML input/select/textarea
    # unfortunately, there aren't any XBlocks for HTML controls, hence reusing GP V1 approach
    question_label = String(
        display_name=_(u"Question label"),
        default="",
        multiline_editor="html"
    )

    question_content = String(
        display_name=_(u"Question content"),
        help=_(u"HTML control"),
        default="",
        multiline_editor="xml"
    )

    required = Boolean(
        display_name=_(u"Required"),
        default=False
    )

    grade = Boolean(
        display_name=_(u"Grading"),
        help=_(u"IF True, answers to this question will be used to calculate student grade for Group Project."),
        default=False
    )

    single_line = Boolean(
        display_name=_(u"Single line"),
        help=_(u"If True question label and content will be displayed on single line, allowing for more compact layout."
               u"Only affects presentation."),
        default=False
    )

    question_css_classes = String(
        display_name=_(u"CSS classes"),
        help=_(u"CSS classes to be set on question element. Only affects presentation.")
    )

    editable_fields = (
        "question_id", "question_label", "question_content", "required", "grade", "single_line", "question_css_classes"
    )

    @lazy
    def stage(self):
        return self.get_parent()

    def render_label(self):
        try:
            label_node = ET.fromstring(self.question_label)
        except ET.ParseError as exception:
            log.exception(exception)
            return ""

        if len(inner_html(label_node)) > 0:
            label_node.set('for', self.question_id)
            current_class = label_node.get('class')
            label_classes = ['prompt']
            if current_class:
                label_classes.append(current_class)
            if self.single_line:
                label_classes.append('side')
            label_node.set('class', ' '.join(label_classes))
        return outer_html(label_node)

    def render_content(self):
        try:
            answer_node = ET.fromstring(self.question_content)
        except ET.ParseError as exception:
            log.exception(exception)
            return ""

        answer_node.set('name', self.question_id)
        answer_node.set('id', self.question_id)
        current_class = answer_node.get('class')
        answer_classes = ['answer']
        if current_class:
            answer_classes.append(current_class)
        if self.single_line:
            answer_classes.append('side')
        if self.stage.is_closed:
            answer_node.set('disabled', 'disabled')
        else:
            answer_classes.append('editable')
        answer_node.set('class', ' '.join(answer_classes))

        return outer_html(answer_node)

    def student_view(self, context):
        question_classes = ["question"]
        if self.required:
            question_classes.append("required")
        if self.question_css_classes:
            question_classes.append(self.question_css_classes)

        fragment = Fragment()
        context = {
            "question_classes": " ".join(question_classes),
            "question_label": self.render_label(),
            "question_content": self.render_content
        }
        fragment.add_content(loader.render_template("templates/html/components/review_question.html", context))
        return fragment

    def studio_view(self, context):
        fragment = super(GroupProjectReviewQuestionXBlock, self).studio_view(context)

        # TODO: StudioEditableXBlockMixin should really support Codemirror XML editor
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/question_edit.css"))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, "public/js/question_edit.js"))
        fragment.initialize_js("GroupProjectQuestionEdit")
        return fragment

    def author_view(self, context):
        fragment = self.student_view(context)
        fragment.add_css_url(self.runtime.local_resource_url(self, "public/css/question_edit.css"))
        return fragment


class GroupProjectReviewAssessmentXBlock(XBlock, StudioEditableXBlockMixin):
    CATEGORY = "group-project-v2-review-assessment"

class GroupActivityQuestion(object):
    def __init__(self, doc_tree, stage):

        self.id = doc_tree.get("id")  # pylint: disable=invalid-name
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")
        self.stage = stage
        self.required = (doc_tree.get("required", "true") == "true")
        designer_class = doc_tree.get("class")
        self.question_classes = ["question"]
        self.grade = doc_tree.get("grade") == "true"

        if self.required:
            self.question_classes.append("required")
        if designer_class:
            self.question_classes.append(designer_class)

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        current_class = answer_node.get('class')
        answer_classes = ['answer']
        if current_class:
            answer_classes.append(current_class)
        if self.small:
            answer_classes.append('side')
        if self.stage.is_closed:
            answer_node.set('disabled', 'disabled')
        else:
            answer_classes.append('editable')
        answer_node.set('class', ' '.join(answer_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        label_html = ''
        label_node = copy.deepcopy(self.label)
        if len(inner_html(label_node)) > 0:
            label_node.set('for', self.id)
            current_class = label_node.get('class')
            label_classes = ['prompt']
            if current_class:
                label_classes.append(current_class)
            if self.small:
                label_classes.append('side')
            label_node.set('class', ' '.join(label_classes))
            label_html = outer_html(label_node)

        return '<div class="{}">{}{}</div>'.format(
            ' '.join(self.question_classes),
            label_html,
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html


class GroupActivityAssessment(object):
    def __init__(self, doc_tree):

        self.id = doc_tree.get("id")  # pylint: disable=invalid-name
        self.label = doc_tree.find("./label")
        answer_node = doc_tree.find("./answer")
        self.answer = answer_node[0]
        self.small = (answer_node.get("small", "false") == "true")

    @property
    def render(self):
        answer_node = copy.deepcopy(self.answer)
        answer_node.set('name', self.id)
        answer_node.set('id', self.id)
        answer_classes = ['answer']
        if self.small:
            answer_classes.append('side')
        current_class = answer_node.get('class')
        if current_class:
            answer_classes.append(current_class)
        answer_node.set('class', ' '.join(answer_classes))

        label_node = copy.deepcopy(self.label)
        label_node.set('for', self.id)
        current_class = label_node.get('class')
        label_classes = ['prompt']
        if current_class:
            label_classes.append(current_class)
        if self.small:
            label_classes.append('side')
        label_node.set('class', ' '.join(label_classes))

        # TODO: this exactly matches answer_html property below
        ans_html = outer_html(answer_node)
        if len(answer_node.findall('./*')) < 1 and ans_html.index('>') == len(ans_html) - 1:
            ans_html = ans_html[:-1] + ' />'

        return "{}{}".format(
            outer_html(label_node),
            ans_html,
        )

    @property
    def answer_html(self):
        html = outer_html(self.answer)
        if len(self.answer.findall('./*')) < 1 and html.index('>') == len(html) - 1:
            html = html[:-1] + ' />'

        return html
