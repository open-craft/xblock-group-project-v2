# Group Work v2 deployment 

Right now Group Work v2 is not working in a Dogwood Edx installation, it requires a `edx-solutions` fork of the 
platform, as it extensively uses the `edx-solutions` api. Some of the administrative tasks are also currently
performed using proprietary Apros interface. 

In order to have a working Group Project you'll need to complete three steps:

1. Set up environment configuration variables
2. Author the XBlock in Studio
3. Configure Group Project in Apros (3rd party LMS) 

## Apros configuration

See corresponding document in Apros (TBD)

![High level deployment overview](images/uml/high-level-architecture.png)

# Setup

In order to use Group Project XBlock v2 in a course, XBlock must be installed into LMS environment and enabled in 
course's advanced settings. Also, Group Project XBlock uses a number of instance-specific configuration variables, so 
setting them is considered a part of setup process.

## Installing XBlock into LMS

If you're using edx-solutions/edx-platform fork, Group Project v2 XBlock is already installed. Otherwise, installing 
Group Project XBlock v2 is done the very same way other XBlocks are installed:

1. Open terminal (or shell) to the LMS instance.
2. Switch to LMS virtualenv
3. pip install -e git+https://github.com/open-craft/xblock-group-project-v2.git@ **version_hash** #egg=xblock-group-project-v2

*version_hash* is the hash of the git commit. By the time of writing, latest stable version was `4322ca8092c5385d5602143077e388017fcb1249`,
so the above command looked like this:

    pip install -e git+https://github.com/open-craft/xblock-group-project-v2.git@4322ca8092c5385d5602143077e388017fcb1249#egg=xblock-group-project-v2
    
## Setting configuration variables

There are two sources of configuration variables: Django settings and XBlock-specific settings available 
through [SettingsService][settings-service]. Both types of settings can be set via LMS environment file `lms.env.json`
or (not recommended) directly in instance Django settings.

[settings-service]: https://github.com/edx/edx-platform/blob/master/common/lib/xmodule/xmodule/services.py#L7

The following Django settings are used:

* `EDX_API_KEY`: string - must contain a edX API Key. As this XBlock uses edX API extensively, failure to provide 
    the key will prevent Group Project XBlock v2 from operating normally.
* `BASE_DIR`: string - base Django instance directory. Used by Submission XBlocks as part of file storage location if
    local file storage is used
* `API_LOOPBACK_ADDRESS`: URL - (optional) should contain base URL of LMS API. Default: http://127.0.0.1:8000
* File upload features piggyback on Django file storage mechanism, in order to store files, a file storage mechanism 
    should be configured *Note:* existing production instances use S3 as file storage; using local file storage is 
    theoretically possible, but it does not work out of the box (likely requires some modifications on LMS/Apros side).

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
    * `group_id`: ID of workgroup to review.
    * `activity_id`: ID of activity to show  - ActivityXBlock usage locator.

* `ta_roles`: list of strings - List of course-specific roles that grant Teaching Assistant access to a course.

* `access_dashboard_for_all_orgs_groups`: list of strings -  List of instance-wide roles that grant access to any 
    organization.

* `access_dashboard_groups`: list of strings - List of instance-wide roles that grant access to admin dashboard.
  Members of these roles will only see users from their own organisation. 

* `access_dashboard_ta_groups`: lis of strings - List of instance-wide roles that grant access to admin dashboard.
  Members of these roles will be able to visit the dashboard only if they are TA for particular course (see `ta_roles`). 

If both `access_dashboard_for_all_orgs_groups` and `access_dashboard_role_groups` are empty or missing, admin dashboard 
is effectively disabled.

Example configuration:

    "XBLOCK_SETTINGS": {
      "group_project_v2": {
        "dashboard_details_url": "/admin/workgroup/dashboard/programs/{program_id}/courses/{course_id}/projects/{project_id}/details?activate_block_id={activity_id}",
        "ta_review_url": "/courses/{course_id}/group_work/{group_id}?activate_block_id={activate_block_id}",
        "access_dashboard_for_all_orgs_groups": ["mcka_role_mcka_admin"],
        "access_dashboard_groups": ["mcka_role_client_admin", "mcka_role_internal_admin"],
        "access_dashboard_ta_groups": ["mcka_role_mcka_ta"],
        "ta_roles": ["assistant"]
      }
    }
    
    
## Enabling Group Project XBlock v2 in a course

To enable the use of Group Project XBlock v2 in the course:

1. Open the course in Studio.
2. In the top menu choose Settings -> Advances Settings
3. Add `gp-v2-project` to "Advanced Module List"
4. Optionally, add `ooyala-player` to "Advanced Module List" - this player is used for video resources

As a result, `Advanced Module List` option should look like that (provided there are no other advanced modules are 
enabled for course): 
![Advanced Module List Image](/docs/images/advanced_module_list.png)


## (Optional) Notifications integration

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

# External/API dependencies of GWv2 

Below is a list of a non-standard dependencies of student-facing functionalities of GWv2. 

## XBlock services

* `settings` GWv2 extensively uses settings defined in `XBLOCK_SETTINGS` in edx lms configuration. It uses
  `group_project_v2` namespace. Note this service is present in LMS. 
* `notifications` Used to send notifications to students events like:   
    * Project stage submissions opened. 
    * Project stage submissions due.
    * File has been uploaded 
    * Grades have been posted.   
    Please see `StageNotificationsMixin` that contains all our usages of notifications API. 
* `courseware_parent_info` Still listed as a required plugin for `GroupActivityXBlock`. 
   
  Note: Most probably can be safely removed, it was introduced in the first version of Group Work XBlock
  and all references to this [service have been removed][removal-of-courseware_parent_info] 
  
[removal-of-courseware_parent_info]: https://github.com/open-craft/xblock-group-project-v2/commit/5f00966d11dec9942ffca73e606c81ce58d23917

## Dependencies in XBlock runtime

* `get_real_user` --- used to get the `id` of the user, which is then used to query API, for 
  `workgroups`, `peer_reviews`, `team_evaluations`, and so forth. Note: this is present in LMS.

## API dependencies

GWv2 extensively uses `edx-solutions` API. 

### User views

* `/api/server/users/:user_id` Used to de-anonymize users (present their name to peers)
* `/api/server/users/preferences` User's TA status is stored in user preferences.
* `/api/server/users/groups` 
    * Groups to be reviewed are stored as `reviewassignment` group, these groups 
      contain a reference to the course and `xblock_id`.
* `/api/server/users/:user_id/workgroups` --- All workgroups student belongs to. 
  This is additionally filtered by `course_id`. 
* `/api/server/users/:user_id/organisations` --- List of organisations user belongs to.
* `/api/server/users/:user_id/groups` --- All groups user belongs to. Used to query
  user permissions (`edx-solutions` uses groups to signify permissions). 

### Group urls 

Group is a good old `django.contrib.auth.models.Group`, with some additional magic 
to store groups: `name`, `type` and `data` (data is a dict of arbitrary data). 

* `/api/server/groups/:group_id/users` Loads users in a group. Used to find the reviewers 
  (see `/api/server/workgroups/:group_id/groups`). 
* `/api/server/groups/:group_id/workgroups` --- used to reverse query workgroups from groups. 
  
### Projects 

Project entity represent a single group project, it has following properties: 

* It is relative to a particular curse (contains course_id)
* It is relative to a particular project XBlock (contains xblock content_id)
* It contains reference to organisation --- which makes this project 
  "private" to members of this organisation. 
* It has a one-to-many relationship with workgroup. 
* `/api/server/projects/` --- used to query workgroups for a given project, 
  project is located using cross section of `course_id` and `content_id` 
* `/api/server/projects/:project_id` --- get project by `project_id` 

### Workgroup endpoints 

Workgroup is a group of users working together on a project, workgroup 
has a one-to-many relationship with Group, each of these groups contains 
users that need to review submissions of this workgroup. These groups 
are sometimes refereed as `assignments`. 

Endpoints include: 

* `/api/server/workgroups` --- create/read workgroups 
* `/api/server/workgroups/:group_id/peer_reviews` --- Retrieves all peer reviews 
  related to team evaluations for a given activity
* `/api/server/peer_reviews` --- Stores, updates, deletes all peer reviews for a given activity
* `/api/server/workgroups/:group_id/workgroup_reviews` --- Retrieves workgroup reviews. Workgroup reviews 
   are related to Peer Grading. 
* `/api/server/workgroup_reviews` creates updates deletes all workgroup reviews 
* `/api/server/workgroups/:group_id/grades` --- sets grade for group, which in turn adds grade 
   for every user
* `/api/server/workgroups/:group_id/groups` --- A number of groups can be attached to workgroup, 
  each contains students that will review this group (as part of peer assessment). 
  These groups have type of `reviewassignment` and store reference to `activity id`. 
* `/api/server/workgroup/:group_id/submissions` --- Lists all submissions done by the users of 
  this group. Submissions are time-stamped so need to be filtered by hand. 
  
## Various other APIs 

* `/api/server/courses/:course_id/roles` used to check whether student is a TA. 

## Proprietary Apros Interface dependencies

* Project is created in inside Apros Interface
* Workgroups are generated inside Apros Interface 
* Review assignments are generated from Apros Interface
* Emails to team-members and TA are done by calling Apros Views. 

## Django dependencies

* `GroupProjectSubmissionXBlock` depends on django [`default_storage`][default-storage] 
   being configured. This dependency is via `UploadFile` class. 
 
[default-storage]: https://docs.djangoproject.com/en/1.9/topics/files/#storage-objects

## Used XBlocks 

* DiscussionXBlock
* OoyalaVideoXBlock
