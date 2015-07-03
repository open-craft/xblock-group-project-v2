import datetime
import ddt
import textwrap
from freezegun import freeze_time


from group_project_v2.components import StageType
from tests.integration.base_test import BaseIntegrationTest, GroupProjectElement


class StageTestBase(BaseIntegrationTest):
    PROJECT_TEMPLATE = textwrap.dedent("""
        <group-project-v2 xmlns:opt="http://code.edx.org/xblock/option">
            <group-project-v2-activity display_name="Activity">
                <opt:data>
                    <![CDATA[
                        <group_activity schema_version='1'>
                            <activitystage {stage_args}>
                                {stage_data}
                            </activitystage>
                        </group_activity>
                    ]]>
                </opt:data>
            </group-project-v2-activity>
        </group-project-v2>
    """)
    stage_type = None

    def build_scenario_xml(self, stage_data, stage_id="stage_id", title="Stage Title", **kwargs):
        stage_arguments = {'id': stage_id, 'title': title, 'type': self.stage_type}
        stage_arguments.update(kwargs)
        stage_args_str = " ".join(
            ["{}='{}'".format(arg_name, arg_value) for arg_name, arg_value in stage_arguments.iteritems()]
        )

        return self.PROJECT_TEMPLATE.format(stage_args=stage_args_str, stage_data=stage_data)

    def prepare_page(self, scenario_xml, view_name='student_view', student_id=1):
        self.load_scenario_xml(scenario_xml)
        scenario = self.go_to_view(view_name=view_name, student_id=student_id)
        self.page = GroupProjectElement(self.browser, scenario)
        self.activities_map = self.get_activities_map()
        return self.page

    def get_stage(self, group_project):
        stage_element = group_project.activities[0].stages[0]
        self.assertTrue(stage_element.is_displayed())
        return stage_element


@ddt.ddt
class CommonStageTest(StageTestBase):
    stage_type = StageType.NORMAL

    @ddt.data(
        # no open and close date - should be empty
        (datetime.datetime(2015, 1, 1), None, None, None),
        # no close, after open - should be empty
        (datetime.datetime(2015, 1, 2), datetime.datetime(2015, 1, 1), None, None),
        # no close, before open - should be opens Jan 02
        (datetime.datetime(2015, 1, 1), datetime.datetime(2015, 1, 2), None, "opens Jan 02"),
        # no close, before open, not same year - should be opens Jan 02 2015
        (datetime.datetime(2014, 1, 1), datetime.datetime(2015, 1, 2), None, "opens Jan 02 2015"),
        # no open, before close, should be due June 12
        (datetime.datetime(2015, 5, 12), None, datetime.datetime(2015, 6, 12), "due Jun 12"),
        # after open, before close, should be due June 12
        (datetime.datetime(2015, 5, 12), datetime.datetime(2015, 5, 1), datetime.datetime(2015, 6, 12), "due Jun 12"),
        # no open, before close, not same year - should be due June 12 2015
        (datetime.datetime(2014, 6, 22), None, datetime.datetime(2015, 6, 12), "due Jun 12 2015"),
        # after close - should be closed June 12
        (datetime.datetime(2015, 6, 13), None, datetime.datetime(2015, 6, 12), "closed on Jun 12"),
    )
    @ddt.unpack
    def test_open_close_label(self, mock_now, open_date, close_date, expected_label):
        date_format = "%m/%d/%Y"
        kwargs = {}
        if open_date is not None:
            kwargs['open'] = open_date.strftime(date_format)
        if close_date is not None:
            kwargs['close'] = close_date.strftime(date_format)

        with freeze_time(mock_now):
            scenario_xml = self.build_scenario_xml("", **kwargs)

            stage_element = self.get_stage(self.prepare_page(scenario_xml))
            self.assertEqual(stage_element.open_close_label, expected_label)


@ddt.ddt
class NormalStageTest(StageTestBase):
    stage_type = StageType.NORMAL

    @ddt.data(
        "I'm content",
        "<p>I'm HTML content</p>",
        '<div><p>More complex<span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>'
    )
    def test_rendering(self, content):
        stage_content_xml = "<content>{content}</content>".format(content=content)
        scenario_xml = self.build_scenario_xml(stage_content_xml)

        stage_element = self.get_stage(self.prepare_page(scenario_xml))
        stage_content = stage_element.content.get_attribute('innerHTML').strip()
        self.assertEqual(stage_content, content)


@ddt.ddt
class UploadStageTest(StageTestBase):
    stage_type = StageType.UPLOAD

    @ddt.data(
        "I'm content",
        "<p>I'm HTML content</p>",
        '<div><p>More complex<span class="highlight">HTML content</span></p><p>Very complex indeed</p></div>'
    )
    def test_rendering(self, content):
        stage_content_xml = "<content>{content}</content>".format(content=content)
        scenario_xml = self.build_scenario_xml(stage_content_xml)

        stage_element = self.get_stage(self.prepare_page(scenario_xml))
        stage_content = stage_element.content.get_attribute('innerHTML').strip()
        self.assertEqual(stage_content, content)
