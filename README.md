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

### Group Project building blocks

The following blocks are a part of Group Project XBlock v2.

#### Top-level XBlocks

* ` Group Project` - top level XBlock, represents entire group project as a whole
    * Settings:
        * `Display Name` - human-friendly name for Group Project - displayed in admin console.
    * Components: 
        * `Group Project Activity` - multiple instances.
        * [`Group Project Navigator`](#project-navigator-and-views) - single instance
        * `Discussion` - external XBlock: see https://github.com/edx-solutions/xblock-discussion; single instance
* `Group Project Activity` - represents single activity in group project, grading happens at this level, hence the block
    carries settings for grading
    * Components:
        * `Display Name` - human-friendly activity name - appears in admin console and in Project Navigator (i.e. 
            visible both to students and course staff)
        * `Weight` - grading attribute - the higher the weight the more influential this activity compared to other
            graded exercises in the same grading bucket (including group project activities and graded excercises)
        * `Reviews Required Minimum` - Peer Grading attribute - sets a number of reviews to be received by a workgroup
            so it can be graded. If set to 0 (zero), activity is considered TA-graded.
        * `User Reviews Required Minimum` - Peer Grading attribute - the minimum number of other-group reviews that an 
            individual student should perform.
        * `Due Date` - Activity due date - displayed to students in Apros progress page. Does not actually prevent users
            from uploading submissions, casting reviews and other group project related activities as it is superceded 
            by individual stages due dates. Informational only.
    * Components:
        * [Stages XBlocks](#stages-xblocks) - multiple instances
        
#### Project Navigator and Views

Project Navigator XBlock is designed to allow quick access to Navigation and other commonly used group project features.

* `Group Project Navigator` - top level Project Navigator XBlock. Can contain multiple Project Navigator View XBlocks 
    (one per type at most), and allows switching between the views.
    * Settings - none
    * Components (single instance per type):
        * `Navigation View` - provides group project navigation capabilities. **Required.**
        * `Submission View` - lists all the required submissions, provides options to upload a submission, 
            review and re-upload previous submissions.
        * `Resources View` - lists all the resources configured for group project.
        * `Ask a TA View` - provides simple interface to message course TA.
        * `Private Discussion View` - opens private discussion XBlock. Requires `Discussion` to be added to root `Group
            project` XBlock.
            
**Important note:** Neither `Group Project Navigator` nor navigation view XBlocks have any configurable settings.
        
#### Stages XBlocks

Stages XBlocks provides core functionality to the group project. There are multiple types of stages, each encapsulating 
one of the possible steps towards project completion. Unlike other XBlocks, stages have some common settings and can
use some common components:

* Common settings:
    * `Display Name` - human-friendly stage name - appears in admin console and in Project Navigator (i.e. 
        visible both to students and course staff). Default: some sensible name for a stage (different per stage type)
    * `Open Date` - sets stage open date - the date when stage becomes available to the students, so that students can
        start perform actions on that stage (upload submission, cast a review, etc.). Default: no open date - stage is
        available right away. 
    * `Close Date` - sets stage close date - the date when stage becomes closed, so students can no longer perform 
        actions on that stage. Default: no close date - stage is always available. 
    * `Hide stage type label` - governs stage appearance in Project Navigator view. If set to True, stage Display Name
        will be prefixed with stage type (i.e. `Overview`, `Task`, `Review`, etc.) in project navigation. 
        Otherwise, Display Name is displayed as is. Default: True
* Common components:
    * `HTML` - HTML XBlock provided by edX platform - contains arbitrary HTML markup (text, images, etc.)
    * `Resource` - group project resource XBlock - see [Stage components](#stage-components) section for details
    * `VideoResource` - group project resource XBlock - see [Stage components](#stage-components) section for details
    * `Project Team` - project team XBlock - see [Stage components](#stage-components) section for details
        
Available stage types:

* `Text` - simple stage displaying a course author-defined text, images, etc.
    * Settings - no stage-specific settings
    * Components - no stage-specific components
    * Completion criteria: completed when user first visits it when the stage is open.
* `Completion` - similar to `Text` staqge, but requires user interaction to be marked as completed - checking a 
    checkbox. Note that checkbox becomes disabled when checked, so it's not possible for a student to cancel 
    "stage completed" action.
    * Settings - no stage-specific settings
    * Components - no stage-specific components
    * Completion criteria: completed when user checks a checkbox "Yes, I have completed this task"
* `Deliverable` - stage that specifies the list of group submissions.
    * Settings - no stage-specific settings
    * Components:
        * `Submissions Help Text` - static (developer-defined) help text instructing students to open Project Navigator
            Submissions view to upload submissions. Help text contains a link that opens the view automatically.
        * `Submission` - specifies one deliverable (aka submission) - see [Stage components](#stage-components) section 
            for details.
    * Completion criteria: completed when all the submissions are uploaded. Note that submissions are required on group
        basis rather than on individual basis, so all the students in the group get this stage completed as soon as
        any of them uploads last submission. It does not matter which student uploads the submission - all uploads
        count towards entire group progress.
* `Team Evaluation` - allows students to provide anonymous feedback to their teammates.
    * Settings - no stage-specific settings
    * Components:
        * `Teammate selector` - displays a list of teammates. **Required, one at most**
        * `Grade Rubric Help Text` - static (developer-defined) help text instructing students to open Project Navigator
            Resources view to access group project documetns on grading. Help text contains a link that opens the view 
            automatically.
        * `Review Question` - represents review question - see [Stage components](#stage-components) section for details
    * Completion criteria: completed when student provided answers to all required questions for all teammates.
* `Peer Grading` - allows students and/or TAs to provide anonymous feedback and grades to other groups.
    * Settings - no stage-specific settings
    * Components:
        * `Group selector` - displays a list of groups student should grade. **Required, one at most**
        * `Grade Rubric Help Text` - static (developer-defined) help text instructing students to open Project Navigator
            Resources view to access group project documetns on grading. Help text contains a link that opens the view 
            automatically.
        * `Review Question` - represents review question - see [Stage components](#stage-components) section for details
    * Completion criteria: completed when student provided answers to all required questions for all groups assigned 
        for review.
* `Evaluation Display` - displays teammate feedback for students
    * Settings - no stage-specific settings
    * Components:
        * `Team Evaluation Display` - block that displays teammates' answers to one of the review questions. 
            See [Stage components](#stage-components) section for details.
    * Completion criteria: completed when user first visits it when the stage is open and teammates have competed their
        reviews - provided answers to all the required questions chosen in `Team Evaluation Display` blocks.
* `Grade Display` - displays group feedback and grades from students and/or TAs 
    * Settings - no stage-specific settings
    * Components:
        * `Grade Evaluation Display` - block that displays other students' and/or TAs answers to one of the review 
            questions. See [Stage components](#stage-components) section for details.
    * Completion criteria: completed when user first visits it when the stage is open and grades are available - when 
        other students and/or TAs provided answers to all the required questions chosen in `Grade Evaluation Display` 
        blocks.
            
            
#### Stage components

## Apros configuration

See corresponding document in Apros (TBD)

# Development


## Development Install


## Running Tests

## Continuous Integration build
