import ddt
import textwrap
from tests.integration.base_test import BaseIntegrationTest, GroupProjectElement


class StageTestBase(BaseIntegrationTest):
    PROJECT_TEMPLATE = textwrap.dedent("""
        <group-project-v2 xmlns:opt="http://code.edx.org/xblock/option">
            <group-project-v2-activity display_name="Activity">
                <opt:data>
                    <![CDATA[
                        <group_activity schema_version='1'>
                            <activitystage id="{id}" title="{title}">
                                {stage_data}
                            </activitystage>
                        </group_activity>
                    ]]>
                </opt:data>
            </group-project-v2-activity>
        </group-project-v2>
    """)

    def build_scenario_xml(self, stage_data, id="stage_id", title="Stage Title"):
        return self.PROJECT_TEMPLATE.format(id=id, title=title, stage_data=stage_data)

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
class NormalStageTest(StageTestBase):
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
