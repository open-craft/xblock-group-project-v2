xblock-group-project-v2
=======================

This XBLock is experimental reimplementation of [Group Project XBlock](https://github.com/edx-solutions/xblock-group-project).

It does *not* work properly in LMS yet.

Configuration variables
-----------------------

This block uses following configuration variables in the ``XBLOCK_SETTINGS``:

    "XBLOCK_SETTINGS": {
      "group_project_v2": {
        "dashboard_details_url": "/admin/workgroup/dashboard/programs/{program_id}/courses/{course_id}/projects/{project_id}/details?activate_block_id={activity_id}",
        "ta_review_url": "/courses/{course_id}/group_work/{group_id}?activate_block_id={activate_block_id}",
        "access_dashboard_for_all_orgs_groups": ["super_admin"],
        "access_dashboard_groups": ["client_admin"],
        "ta_roles": ["assistant"]
      }
    },

These settings have following meanings:

* ``dashboard_details_url``: url pattern used to generate details url in the
  dashboard. It uses following parameters in ``str.format`` style:

  * ``program_id``: Id of course group this activity belong to
  * ``course_id``: Id of course this activity belong to
  * ``project_id``: Id of group project to show
  * ``activity_id``: Xblock activity to show

* ``ta_review_url``: url pattern used to render the review url for the TA,
  parameters used have the same meaning as in above urlpattern,
  with additional ``group_id``, meaning id of group of students.

* ``ta_roles``: List of names of course roles user. If logged in user has any
  role from this set for a given course, he is assumed to be a TA for that course.

* ``access_dashboard_for_all_orgs_groups``: List of names of groups of users,
  if a user belongs to any group in this list, he can access dashboard and see
  all work groups.

* ``access_dashboard_groups``: List of names of groups of users,
  if a user belongs to any group in this list, he can access the dashboard and
  see groups containing students from any organisation he belongs to.

If both ``access_dashboard_for_all_orgs_groups`` and ``access_dashboard_role_groups``
are empty or missing, dashboard is effectively disabled.

### Example configuration

    "XBLOCK_SETTINGS": {
      "group_project_v2": {
        "dashboard_details_url": "/admin/workgroup/dashboard/programs/{program_id}/courses/{course_id}/projects/{project_id}/details?activate_block_id={activity_id}",
        "ta_review_url": "/courses/{course_id}/group_work/{group_id}?activate_block_id={activate_block_id}",
        "access_dashboard_for_all_orgs_groups": ["mcka_role_mcka_admin"],
        "access_dashboard_groups": ["mcka_role_client_admin", "mcka_role_internal_admin"],
        "ta_roles": ["assistant"]
      }
    }