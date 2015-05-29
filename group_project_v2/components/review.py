import copy
from group_project_v2.utils import outer_html, inner_html


class GroupActivityQuestion(object):
    def __init__(self, doc_tree, stage):

        self.id = doc_tree.get("id")
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

        self.id = doc_tree.get("id")
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