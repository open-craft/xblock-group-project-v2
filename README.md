xblock-group-project-v2
=======================

This XBLock is experimental reimplementation of [Group Project XBlock](https://github.com/edx-solutions/xblock-group-project).

It does *not* work properly in LMS yet.

Features
--------

Installation
------------

Configuration
=============

In order to have a working Group Project, one need three components:
1. Author the XBlock in Studio
2. Set up environment configuration variables
3. Configure Group Project in Apros (3rd party LMS) 

Authoring
---------

Configuration variables
-----------------------

There are two sources of configuration variables: django settings and XBlock-specific settings available 
through [SettingsService][settings-service].

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

Apros configuration
-------------------

See corresponding document in Apros (TBD)

Development
===========

Development Install
-------------------

Running Tests
-------------

Continuous Integration build
----------------------------

    