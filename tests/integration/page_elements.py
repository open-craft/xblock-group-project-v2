"""
This module contains classes representing various GroupProject page elements
"""
from builtins import next
from builtins import object
from lazy.lazy import lazy
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from group_project_v2.project_navigator import ViewTypes
from group_project_v2.stage.utils import StageState, ReviewState


class BaseElement(object):
    """
    This is a lightweight adaptation of :class:`bok_choy.PageObject` class to operate with the following constraints:
        * Most tests run on a single page
        * There can be multiple instances of the same type of object on the same page.
        * There are no urls to visit - subclasses represent page elements on the same page

    As a result `url` and `visit` does not do anything, and `is_browser_on_page` check is virtually equivalent to
    `NoSuchElementException` when locating the element.

    Page queries (performed via `q` helper) have some drawbacks as well:
        * They are performed in scope of the entire page
        * There are no means of returning specific PageObject subclass from `q` query.

    """
    def __init__(self, browser, element):
        """
        Initialization.
        """
        self._browser = browser
        self._element = element

    @property
    def browser(self):
        """
        Returns selenium browser object (:class:`WebDriver`)
        """
        return self._browser

    @property
    def element(self):
        """
        Returns dom element wrapper object (:class:`WebElement`)
        """
        return self._element

    def make_element(self, dom_element, element_type):
        """
        Wraps dom_element (:class:`WebElement`) into a BaseElement object of element_type class
        """
        if isinstance(dom_element, str):
            dom_element = self.element.find_element_by_css_selector(dom_element)
        return element_type(self.browser, dom_element)

    def make_elements(self, css_selector, element_type):
        """
        Wraps DOM elements (:class:`WebElement`) matching css_selecotr into a BaseElement object of element_type class
        """
        elements = self.element.find_elements_by_css_selector(css_selector)
        return [self.make_element(elem, element_type) for elem in elements]

    def click(self):
        self.element.click()

    def is_displayed(self):
        return self.element.is_displayed()


class GroupProjectElement(BaseElement):
    """ Wrapper around group project xblock element """
    ACTIVITY_CSS_SELECTOR = ".group-project-content .xblock-v1[data-block-type='gp-v2-activity']"

    @property
    def activities(self):
        return self.make_elements(self.ACTIVITY_CSS_SELECTOR, ActivityElement)

    @property
    def project_navigator(self):
        return self.make_element(
            self.element.find_element_by_css_selector("[data-block-type='gp-v2-navigator']"),
            ProjectNavigatorElement
        )

    def get_activity_by_id(self, activity_id):
        activity_selector = self.ACTIVITY_CSS_SELECTOR + "[data-usage='{}']".format(activity_id)
        activity_element = self.element.find_element_by_css_selector(activity_selector)
        return self.make_element(activity_element, ActivityElement)

    def find_stage(self, activity_id, stage_id):
        activity_selector = self.ACTIVITY_CSS_SELECTOR + "[data-usage='{}']".format(activity_id)
        stage_selector = "#activity_" + stage_id
        activity_element = self.element.find_element_by_css_selector(activity_selector)
        return activity_element.find_element_by_css_selector(stage_selector)


class ActivityElement(BaseElement):
    """ Wrapper around group project activity xblock element """
    STAGE_CSS_SELECTOR = "div.activity_section"

    @property
    def id(self):
        return self.element.get_attribute('data-usage')

    @property
    def stages(self):
        return self.make_elements(self.STAGE_CSS_SELECTOR, StageElement)

    def get_stage_by_id(self, stage_id):
        stage_selector = self.STAGE_CSS_SELECTOR + "#" + stage_id.replace(".", "\\.")
        stage_element = self.element.find_element_by_css_selector(stage_selector)
        return self.make_element(stage_element, StageElement)


class StageElement(BaseElement):
    """ Base class for stage wrapper elements """
    @property
    def id(self):
        return self.element.get_attribute('id').replace('activity_', '')

    @property
    def title(self):
        return self.element.find_element_by_css_selector('h1 .stage_title').text

    @property
    def open_close_label(self):
        try:
            element = self.element.find_element_by_css_selector('h1 .highlight')
            return element.text
        except NoSuchElementException:
            return None

    @property
    def content(self):
        return self.element.find_element_by_css_selector('.stage_content')

    @property
    def has_admin_grading_notification(self):
        try:
            self.element.find_element_by_css_selector(".grading_override.ta_graded")
            return True
        except NoSuchElementException:
            return False


class ReviewStageElement(StageElement):
    """ Wrapper around group project review stage element """
    @property
    def form(self):
        return self.make_element(self.element.find_element_by_css_selector('div.review'), ReviewFormElement)

    @property
    def peers(self):
        return self.make_elements(".peers.review_subjects .select_peer", ReviewObjectSelectorElement)

    @property
    def groups(self):
        return self.make_elements(".groups.review_subjects .select_group", ReviewObjectSelectorElement)

    @property
    def other_submission_links_popup(self):
        return self.make_element(
            self.element.find_element_by_css_selector(".review_submissions_dialog"), ReviewSubmissionsDialogPopup
        )


class ReviewObjectSelectorElement(BaseElement):
    """ Wrapper around review object selector elements """
    allowed_state_classes = {ReviewState.NOT_STARTED, ReviewState.INCOMPLETE, ReviewState.COMPLETED}

    @property
    def name(self):
        return self.element.get_attribute('title')

    @property
    def subject_id(self):
        return self.element.get_attribute('data-id')

    @property
    def review_status(self):
        state_icon_element = self.element.find_element_by_css_selector(".group-project-review-state")
        css_classes = state_icon_element.get_attribute("class").split()
        review_classes = [css_class for css_class in css_classes if css_class in self.allowed_state_classes]
        assert len(review_classes) <= 1
        return review_classes[0] if review_classes else ReviewState.NOT_STARTED

    def open_group_submissions(self):
        self.element.find_element_by_css_selector(".view_other_submissions").click()


class ReviewSubmissionsDialogPopup(BaseElement):
    @property
    def stage_submissions(self):
        return self.make_elements(".other-team-submission", OtherTeamStageSubmissionsElement)


class OtherTeamStageSubmissionsElement(BaseElement):
    @property
    def title(self):
        return self.element.find_element_by_css_selector("h4").text

    @property
    def uploads(self):
        return self.make_elements("ul.group-project-submissions li", OtherTeamSubmissionElement)


class OtherTeamSubmissionElement(BaseElement):
    def __init__(self, browser, element):
        super(OtherTeamSubmissionElement, self).__init__(browser, element)
        self._uploaded_by = None
        try:
            self.element.find_element_by_css_selector(".no_submission")
            self.no_upload = True
        except NoSuchElementException:
            self._link = self.element.find_element_by_tag_name("a")
            self.no_upload = False

            try:
                self._uploaded_by = self.element.find_element_by_css_selector(".upload_item_data")
            except NoSuchElementException:
                pass

    @property
    def title(self):
        if self.no_upload:
            return self.element.find_element_by_css_selector(".no_submission").text
        return self._link.text

    @property
    def link(self):
        if self.no_upload:
            return None
        return self._link.get_attribute('href').rstrip('/')

    @property
    def filename(self):
        if self.no_upload:
            return None
        return self.element.find_element_by_css_selector('.upload_filename').text.strip('()')

    @property
    def uploaded_by(self):
        if self.no_upload:
            return None
        if self._uploaded_by is not None:
            return self._uploaded_by.text
        return None

    @property
    def upload_data_available(self):
        return self._uploaded_by is not None


class ReviewFormElement(BaseElement):
    def _get_hidden_input_value(self, input_name):
        return self.element.find_element_by_css_selector("input[name='{}']".format(input_name)).get_attribute('value')

    def _get_review_subject_id(self, css_selector):
        try:
            selected_teammate_element = self.element.find_element_by_css_selector(css_selector)
            selected_teammate = self.make_element(selected_teammate_element, ReviewObjectSelectorElement)
            return int(selected_teammate.subject_id)
        except NoSuchElementException:
            return None

    @property
    def peer_id(self):
        return self._get_review_subject_id(".peers.review_subjects .select_peer.selected")

    @property
    def group_id(self):
        return self._get_review_subject_id(".groups.review_subjects .select_group.selected")

    @property
    def questions(self):
        return self.make_elements(".question", ReviewQuestionElement)

    @property
    def submit(self):
        return self.element.find_element_by_css_selector("button.submit")


class ReviewQuestionElement(BaseElement):
    @property
    def label(self):
        return self.element.find_element_by_tag_name("label").text

    @property
    def control(self):
        return self.make_element(self.element.find_element_by_css_selector("input,textarea,select"), InputControl)


class InputControl(BaseElement):
    timeout = 5

    def __getattr__(self, item):
        if hasattr(self.element, item):
            return getattr(self.element, item)
        return self.element.get_attribute(item)

    def _wait_unitl_enabled(self):
        wait = WebDriverWait(self.element, self.timeout)
        wait.until(lambda e: e.is_enabled(), u"{} should be enabled".format(self.element.text))

    def fill_text(self, text):
        self._wait_unitl_enabled()
        self.element.clear()
        self.element.send_keys(text)

    def select_option(self, option_value):
        self._wait_unitl_enabled()
        select = Select(self.element)
        select.select_by_value(option_value)

    @property
    def options(self):
        options = self.element.find_elements_by_tag_name("option")
        if options:
            return {option.get_attribute('value'): option.text for option in options}
        return None


class ProjectNavigatorElement(BaseElement):
    @lazy
    def views(self):
        return self.make_elements(".group-project-navigator-view", ProjectNavigatorViewElement)

    @lazy
    def view_selectors(self):
        return self.make_elements(".view-selector-item", ProjectNavigatorViewSelectorElement)

    @property
    def selected_stage(self):
        nav_view = self.get_view_by_type(ViewTypes.NAVIGATION, NavigationViewElement)
        return nav_view.selected_stage

    def get_view_by_type(self, target_type, view_element_class=None):
        view_element_class = view_element_class if view_element_class else ProjectNavigatorViewElement
        css_selector = ".group-project-navigator-view[data-view-type='{}']".format(target_type)
        element = self.element.find_element_by_css_selector(css_selector)
        return self.make_element(element, view_element_class)

    def get_view_selector_by_type(self, target_type):
        return [view_selector for view_selector in self.view_selectors if view_selector.type == target_type][0]


class ProjectNavigatorViewElement(BaseElement):
    """ Base class for project navigator view content wrappers """
    activity_element_type = None

    @property
    def activities(self):
        return self.make_elements(".group-project-activity-wrapper", self.activity_element_type)

    @property
    def type(self):
        return self.element.get_attribute("data-view-type")

    def close_view(self):
        # pylint: disable=raise-missing-from
        try:
            close_button = self.element.find_element_by_css_selector(".group-project-navigator-view-close")
            close_button.click()
        except NoSuchElementException:
            raise AssertionError("View cannot be closed")


class ProjectNavigatorViewSelectorElement(BaseElement):
    """ Wrapper around view selectors in Project Navigator """
    @property
    def type(self):
        return self.element.get_attribute("data-view-type")


class ProjectNavigatorViewActivityElement(BaseElement):
    """ Represents activity block in Project Navigator activity-related views (resources, submissions, navigation) """
    @property
    def activity_name(self):
        return self.element.find_element_by_css_selector(".group-project-activity-header").text.strip()


class ProjectNavigatorResourcesActivityElement(ProjectNavigatorViewActivityElement):
    @property
    def resources(self):
        resource_elements = self.element.find_elements_by_css_selector("ul.group-project-resources li")
        return [self.make_element(elem, ResourceLinkElement) for elem in resource_elements]


class ProjectNavigatorSubmissionsActivityElement(ProjectNavigatorViewActivityElement):
    @property
    def submissions(self):
        return self.make_elements(".group-project-submissions .uploader", SubmissionUploadItemElement)


class NavigationViewElement(ProjectNavigatorViewElement):
    @property
    def stages(self):
        return self.make_elements(".group-project-stage", StageItemElement)

    def get_stage_by_title(self, stage_title):
        try:
            return next(stage for stage in self.stages if stage.title == stage_title)
        except StopIteration:
            return None

    @property
    def selected_stage(self):
        return self.make_element(
            self.element.find_element_by_css_selector(".group-project-stage.current"), StageItemElement
        )


class ResourcesViewElement(ProjectNavigatorViewElement):
    activity_element_type = ProjectNavigatorResourcesActivityElement


class SubmissionsViewElement(ProjectNavigatorViewElement):
    activity_element_type = ProjectNavigatorSubmissionsActivityElement


class AskTAViewElement(ProjectNavigatorViewElement):
    activity_element_type = None  # this view does not render individual activities

    def _get_textarea(self):
        return self._element.find_element_by_css_selector("form.contact-ta-form textarea[name='ta_message']")

    @property
    def message(self):
        return self._get_textarea().get_attribute('value')

    @message.setter
    def message(self, value):
        self._get_textarea().send_keys(value)

    def submit_message(self):
        self._element.find_element_by_css_selector("form.contact-ta-form input[type=submit]").click()


class StageItemElement(BaseElement):
    def __init__(self, browser, element):
        super(StageItemElement, self).__init__(browser, element)
        self.stage_link = element.find_element_by_css_selector(".group-project-stage-title a")

    @property
    def stage_id(self):
        return self.element.get_attribute("data-stage-id")

    @property
    def activity_id(self):
        return self.stage_link.get_attribute("data-activity-id")

    @property
    def title(self):
        return self.element.find_element_by_css_selector(".group-project-stage-title").text.strip()

    @property
    def state(self):
        classes = set(
            self.element.find_element_by_css_selector(".group-project-stage-state").get_attribute("class").split()
        )
        state_classes = {StageState.COMPLETED, StageState.INCOMPLETE, StageState.NOT_STARTED}
        intersection = (classes & state_classes)
        assert(len(intersection)) == 1
        return intersection.pop()

    def navigate_to(self):
        self.stage_link.click()


class ResourceLinkElement(BaseElement):
    def __init__(self, browser, element):
        super(ResourceLinkElement, self).__init__(browser, element)
        self.resource_link = self.element.find_element_by_css_selector("a")

    @property
    def title(self):
        return self.resource_link.text.strip()

    @property
    def url(self):
        return self.resource_link.get_attribute("href")

    @property
    def video_id(self):
        return self.resource_link.get_attribute("data-video-id")


class SubmissionUploadItemElement(BaseElement):
    @property
    def title(self):
        # last char is always a semicolon
        return self.element.find_element_by_css_selector(".upload_title").text.strip()[:-1]

    @property
    def file_location(self):
        return self.element.find_element_by_css_selector(".upload_item_wrapper").get_attribute("data-location")

    @property
    def upload_item_wrapper(self):
        return self.element.find_element_by_css_selector(".upload_item_wrapper")

    @property
    def file_upload_input(self):
        return self.upload_item_wrapper.find_element_by_css_selector("input")

    @property
    def uploaded_by(self):
        try:
            return self.element.find_element_by_css_selector(".upload_item_data").text.strip()
        except NoSuchElementException:
            return None

    @property
    def upload_enabled(self):
        upload_ctrl = self.element.find_element_by_css_selector(".file_upload")
        return not upload_ctrl.get_attribute('disabled')

    def upload_file_and_return_modal(self, location):

        upload_item = self.element.find_element_by_css_selector(".file_upload")
        self.browser.execute_script(
            "return $(arguments[0]).show()", upload_item)
        upload_item.clear()
        upload_item.send_keys(location)
        return ModalDialogElement(self.browser)


class ModalDialogElement(BaseElement):

    def __init__(self, browser, element=None):
        if element is None:
            element = browser.find_element_by_css_selector(".message")
        super(ModalDialogElement, self).__init__(browser, element)

    def close(self):
        elem = self.element.find_element_by_css_selector(".close-box")
        self.browser.execute_script("return $(arguments[0]).click();", elem)

    @property
    def title(self):
        return self.element.find_element_by_css_selector(".message_title").text

    @property
    def message(self):
        return self.element.find_element_by_css_selector(".message_text").text


class ProjectTeamElement(BaseElement):
    @property
    def team_members(self):
        return [
            element.text
            for element in self.element.find_elements_by_css_selector('.group-project-team-member-name')
        ]
