# xblock-group-project-v2


This XBLock is experimental reimplementation of [Group Project XBlock](https://github.com/edx-solutions/xblock-group-project).

It does *not* work properly in LMS yet.

## Features

* Structure - group project is organized around activities and stages. 
    * Activities are the larger chunks, used to distinguish between logically bound parts of group project. Activities 
      can contain one or more stages. Grading happens at activity level, i.e. one grade per activity.
    * Stages are smaller building blocks, representing individual steps towards project completion.
* Collaborative learning - students are organized into workgroups (aka cohorts) to work on a set of problems in a
  collaborative way.
* Team communication - group project interface allows sending emails to individual teammates or entire workgroup.
* Private discussions - private (aka cohorted) discussions can be configured for the group prohect, to provide platform 
  for discussing the assignments between teammates, and avoid spoiling the results/ideas to other workgroups or future
  course students.
* Resources - course authors can provide a set of resources - videos or documents - to help orient students, provide 
  deliverable templates, or just share some relevant information about the assignment.
* File submissions - outcomes are uploaded to the server, to facilitate sharing them between teammembers and for future
  grading.
* Peer feedback - workgroup members can provide anonymous feedback to each other.
* Grading - activities are either peer-graded or staff-graded:
    * Staff grading - staff members with appropriate roles are asked to provide grade for the workgroup.
    * Peer grading - students are asked to evaluate other workgroups' work.
    * Staff-grading fallback - if some of the students fail to provide grades to other workgroup, staff members can 
      interfere and provide missing grades.
* Omnipresent features - Group Project Navigator is always displayed and provides quick access to most commonly 
  used features:
    * Project navigation - jump to any stage in any activity in one click.
    * Resources panel - all the resources in one place.
    * Submissions panel - upload, view and change deliverables as you go.
    * Private discussions - connect with teammates.
    * Ask Teaching Assistant - ask course staff for help in seconds.

## Setup

In order to use Group Project XBlock v2 in a course, XBlock must be installed into LMS environment and enabled in 
course's advanced settings. Also, Group Project XBlock uses a number of instance-specific configuration variables, so 
setting them is considered a part of setup process.

### Installing XBlock into LMS

If you're using edx-solutions/edx-platform fork, Group Project v2 XBlock is already installed. Otherwise, installing 
Group Project XBlock v2 is done the very same way other XBlocks are installed:

1. Open terminal (or shell) to the LMS instance.
2. Switch to LMS virtualenv
3. pip install -e git+https://github.com/open-craft/xblock-group-project-v2.git@ **version_hash** #egg=xblock-group-project-v2

*version_hash* is the hash of the git commit. By the time of writing, latest stable version was `4322ca8092c5385d5602143077e388017fcb1249`,
so the above command looked like this:

    pip install -e git+https://github.com/open-craft/xblock-group-project-v2.git@4322ca8092c5385d5602143077e388017fcb1249#egg=xblock-group-project-v2
    
### Setting configuration variables

There are two sources of configuration variables: django settings and XBlock-specific settings available 
through [SettingsService][settings-service]. Both types of settings can be set via LMS environment file `lms.env.json`
or (not recommended) directly in instance Django settings.

[settings-service]: https://github.com/edx/edx-platform/blob/master/common/lib/xmodule/xmodule/services.py#L7

The following django settings are used:

* `EDX_API_KEY`: string - must contain a edX API Key. As this XBlock uses edX API extensively, failure to provide 
    the key will prevent Group Project XBlock v2 from operating normally.
* `BASE_DIR`: string - base django instance directory. Used by Submission XBlocks as part of file storage location if
    local file storage is used
* `API_LOOPBACK_ADDRESS`: URL - (optional) should contain base URL of LMS API. Default: http://127.0.0.1:8000
* File upload features piggyback on django file storage mechanism, in order to store files, a file storage mechanism 
    should be configured *Note:* existing production instances use S3 as file storage; using local file storage is not 
    confirmed.

Group Project XBlock v2 uses the following bucket key to access XBlock settings: `group_project_v2`. 
The following XBlock settings are used:

* `dashboard_details_url`: string -  url pattern used to generate details url in the dashboard. 
    It uses following parameters in ``str.format`` style:

  * `program_id`: ID of program this group project belongs to; might belong to multiple programs, injected by runtime
  * `course_id`: ID of course this group project belongs to  - course usage locator
  * `project_id`: ID of group project to show - Apros ID, injected by runtime.
  * `activity_id`: ID of activity to show  - ActivityXBlock usage locator.

* `ta_review_url`: string - url pattern used to render the review url for the TA:
    * `course_id`: ID of course this group project belongs to  - course usage locator
    * `group_id`: ID of workgorup to review.
    * `activity_id`: ID of activity to show  - ActivityXBlock usage locator.

* `ta_roles`: list of strings - List of course-specific roles that grant Teaching Assistant access to a course.

* `access_dashboard_for_all_orgs_groups`: list of strings -  List of instance-wide roles that grant access to any 
    organization.

* `access_dashboard_groups`: list of strings - List of instance-wide roles that grant access to admin dashboard

If both `access_dashboard_for_all_orgs_groups` and `access_dashboard_role_groups` are empty or missing, admin dashboard 
is effectively disabled.

Example configuration:

    "XBLOCK_SETTINGS": {
      "group_project_v2": {
        "dashboard_details_url": "/admin/workgroup/dashboard/programs/{program_id}/courses/{course_id}/projects/{project_id}/details?activate_block_id={activity_id}",
        "ta_review_url": "/courses/{course_id}/group_work/{group_id}?activate_block_id={activate_block_id}",
        "access_dashboard_for_all_orgs_groups": ["mcka_role_mcka_admin"],
        "access_dashboard_groups": ["mcka_role_client_admin", "mcka_role_internal_admin"],
        "ta_roles": ["assistant"]
      }
    }
    
    
### Enabling Group Project XBlock v2 in course

To enable the use of Group Project XBlock v2 in the course:

1. Open the course in Studio.
2. In the top menu choose Settings -> Advances Settings
3. Add `gp-v2-project` to "Advanced Module List"
4. Optionally, add `ooyala-player` to "Advanced Module List" - this player is used for video resources

As a result, `Advanced Module List` option should look like that (provided there are no other advanced modules are 
enabled for course): 
![Advanced Module List Image](/docs/images/advanced_module_list.png)


### (Optional) Notifications integration

Group Project XBlock v2 sends a number of notifications via edx-notifications app. In order to make those notifications
appear correctly, make sure `NOTIFICATION_CLICK_LINK_URL_MAPS` Django setting contains the following record:

    'open-edx.xblock.group-project-v2.*': '/courses/{course_id}/group_work?activate_block_id={location}'
    
If you're using edx-solutions/edx-platform fork, appropriate value is already set. Otherwise, note that 
`NOTIFICATION_CLICK_LINK_URL_MAPS` are read from `lms.env.json`, so they should be modified there.    

Example:

```
NOTIFICATION_CLICK_LINK_URL_MAPS = {
    'open-edx.studio.announcements.*': '/courses/{course_id}/announcements',
    'open-edx.lms.leaderboard.*': '/courses/{course_id}/cohort',
    'open-edx.lms.discussions.*': '/courses/{course_id}/discussion/{commentable_id}/threads/{thread_id}',
    'open-edx.xblock.group-project.*': '/courses/{course_id}/group_work?seqid={activity_location}',
    'open-edx.xblock.group-project-v2.*': '/courses/{course_id}/group_work?activate_block_id={location}',
}
```  


# Configuration

In order to have a working Group Project, one need three components:
1. Author the XBlock in Studio
2. Set up environment configuration variables (covered earlier)
3. Configure Group Project in Apros (3rd party LMS) 

## Authoring

Group Project XBlock v2 relies heavily on "nested XBlocks" feature, provided by edX Platform and XBlocks ecosystem.
To be precise, Group Project is built from smaller XBlocks, each implementing some smaller subset of Group project 
functionality: peer grading, submissions upload, team discussions, etc. Most of these features are internal to Group 
Project XBlock v2 package, but some more advanced features reuse other XBlocks.

Overall, the project structure is the following:

* Group Project XBlock
    * Group Activity XBlock 1
        * Stage XBlock 1
        * Stage XBlock 2
            * Stage component XBlock
            * Stage component XBlock
        * Stage XBlock 3
    * Group Activity XBlock 2
        * Stage XBlock 4
            * Stage Component XBlock
        * Stage XBlock 5
    * Project Navigator XBlock
        * Project Navigation View Xblock
        * Submissions View XBlock
        * Resources View XBlock
        * Private Discussion View XBlock
    * Discussion XBlock
    
In this example Group Project with two activities, Project Navigator and Private Discussions is shown. Activity 1 
is composed of three stages, Activity 2 is composed of two stages. Some stages have stage components - even smaller
building blocks, varied by stage type. Project Navigator have most of the Project Navigator available.

Typical Group Project contains several activities, each of which have multiple stages XBlocks. In addition to that,
Group Project Navigator is a required component, so if it is omitted Group Project XBlock will display validation errors 
in Studio and will display an error message in LMS and Apros. Also, Navigation View is a required component of Project
Navigator, so any correct Group Project XBlock will contain at least Project Navigator with Navigation View in it.

Activities act as a larger chunks of group project by combining stages into a logically bound units. Grading 
happens at activity level.

Each stage represents single group project step - getting acquainted with the team, familiarizing with the task, 
uploading deliverable, providing and receiving grading, etc. Stages are usually built from multiple stage components -
from simple HTML blocks to more sophisticated Project Team and Submission blocks. Also, by using Resource blocks, stage 
can contribute various resources to the project: grading rubrics, submission templates, or any other relevant documents
and video.
 
Available stages and their intended use:
 
* `Text` - simple stage showing some author-defined text.
* `Completion` - almost the same as `Text`, except it requires student to explicitly mark this stage as completed. Use
     for simple non-graded tasks, i.e. "Get acquainted with the team", "Read related chapters in course textbook", etc. 
* `Submission` - at this stage students are asked to upload their deliverables. Most of actual group project work are
   likely to happen during this stage. Use to set up a list of deliverables for an activity and a deadline to upload 
   them. If deliverable templates are provided to students, the best place to place them is stages of this type.
* `Team Evaluation` - allows students to provide anonymous feedback to teammates. Intended use is to allow students
    in the team provide and receive feedback about their team work, role in the team, communication skills, etc.
* `Peer Grading` - this stage, in addition to `Submission` stage forms a backbone of group project. During this stage
    deliverables uploaded earlier are graded by either students in other groups or Teaching Assistants. Grading criteria
    can be delivered to students as contents of this stage or resources on this stage.
* `Evaluation Display` - this stage allows students review their teammate feedback. Use with `Team Evaluation` stage.
* `Grade Display` - this stage allows students review their group grade and feedback received from graders. Use with 
    `Peer Grading` stage.

Detailed list of available XBlocks are [available in the docs folder](/docs/XBlocks.md).

## Apros configuration

See corresponding document in Apros (TBD)

# Development

Short summary: developing on Group Project XBlock v2 and running tests requires, at the minimum:

* python>=2.7,<3.0
* pip>=6.0
* node.js>=0.10
* npm>=1.3.10 (might work with older versions, but not checked)

Other dependencies are installed via `pip install` or `npm install`.

Group Project XBlock v2 contains a Makefile to help with most common operations.

## Development Install

In new virtualenv (or in actual install, if you're feeling brave/careless)

    pip install -r requirements/dev.txt 

should get you up and running. It installs requirements both from `base.txt` (contains "production" dependencies) and 
`test.txt` (test dependencies), as well as Group Project XBlock v2 itself.

## Running Tests

Group Project XBlock v2 contains three kinds of tests: python unit tests, javascript tests an integration tests.

Unit tests are located in `tests/unit` folder. They are lighter, but only test one program "unit" at a time (a signle 
method or property usually). They run relatively fast, so it is a good idea to run them frequently during development 
process.

Integration tests are built on top of selenium and [bok_choy][bok-choy]. They execute a real web server running a XBlock
workbench, so they run time is significantly larger than that of unittests.

Helper file `run_tests.py` is provided to run python unittests and integration tests. It runs Django and workbench
under the hood, so it accepts the same parameters as Django unit test runner.

Examples:

    ./run_tests.py tests/unit - runs all tests in unittest suite
    ./run_tests.py tests/unit/test_mixins.py - runs all tests in test_mixins.py file 
    ./run_tests.py tests/unit/test_mixins.py:TestChildrenNavigationXBlockMixin - runs all tests in TestChildrenNavigationXBlockMixin class
    ./run_tests.py tests/unit/test_mixins.py:TestChildrenNavigationXBlockMixin.test_child_category - runs single test
    
    ./run_tests.py --with-coverage --cover-package=group_project_v2 - run all tests with coverage

Since selenium tests open an actual browser, running them will impede other activities at the machine, as each new 
browser window opened for each test will capture focus. Thus, it is advices to run integration tests using `xvfb-run`. 
Note that some tests will fail if screen size is insufficient, so recommended screen size is 1920x1080x24:

     xvfb-run --server-args="-screen 0, 1920x1080x24" ./run_tests.py tests/integration --with-coverage --cover-package=group_project_v2

[bok-choy]: https://github.com/edx/bok-choy

Javascript tests exercise various javascript components of Group Project XBlock. They are written using [jasmine test
framework][jasmine-test-framework] and are executed by [karma test runner][karma-test-runner]. Karma runs in node.js,
so a compatible version of node.js and npm should be installed.

Karma can run tests in two modes: continuous and single run. Single run mode executes all the tests once and than 
terminates, presenting the results of run. In continuous mode, karma installs watchers on all the files included for the
test run (both actual source files and files with tests) and re-runs the tests each time any file is updated.

It is advised to use continuous mode for development. To start karma runner in development mode, issue the following

    ./node_modules/.bin/karma start tests/js/karma.conf.js
    
Note that by default `karma-coverage` plugin is enabled. As a result, debugging JS tests might be problematic, as it
modifies the source files on the fly by inserting coverage API calls. Simplest way to workaroud that is to comment 
`coverage` reporter in `tests/js/karma.conf.js -> reporters` for the duration of debugging session (suggestions on how 
to do that better are welcome). 

[jasmine-test-framework]: http://jasmine.github.io/edge/introduction.html
[karma-test-runner]: https://karma-runner.github.io/0.13/index.html

## Code quality checks

Code quality assertion tools are used to check both python (pep8 and pylint) and javascript (jshint) code quality.
 
Both `group_project_v2` (actual code) and `tests` (tests, obviously) packages are checked. `pep8` is run with default 
settings, except for `max-line-length=120`. `pylint` uses different pylintrc files for [group_project_v2 package]
[gp-v2-pylintrc] and [tests package][tests-pylintrc].

[gp-v2-pylintrc]: pylintrc
[tests-pylintrc]: tests/pylintrc

Javascript: same as with python code, both actual; code in `group_project_v2/public/js` and tests in `tests/js` are 
checked, except for the vendor files in `group_project_v2/public/js/vendor`. Roughly equivalent jshintrc files are
used for [actual code][gp-v2-jshintrc] and [tests][tests-jshintrc]

[gp-v2-jshintrc]: .jshintrc
[tests-jshintrc]: tests/.jshintrc

[jshintrc]: .jshintrc

## Continuous Integration build

Travis CI build is configured to run on each PR against master. CI build installs Group Project XBlock v2 from scratch,
runs unit, js and integration tests and checks code quality. CI build fails if there are any failing tests or quality
code violations are reported.

Sometimes CI build fails while tests run on development machine pass. To debug such problems, the first step is to 
replicate CI build installation process and run as close as possible:
    * Commands run by CI are listed in `.travis.yml -> install` section.
    * Commands to run tests and quality checks are listed in `.travis.yml -> script` section.

