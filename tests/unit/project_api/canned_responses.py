
class Projects(object):
    project1 = {
        "count": 1,
        "num_pages": 1,
        "current_page": 1,
        "results": [
            {
                "id": 1,
                "url": "/api/server/projects/1/",
                "created": None, "modified": None,
                "course_id": "MyCompany/GP2/T2",
                "content_id": "i4x://MyCompany/GP2/gp-v2-project/abcdefghijklmnopqrstuvwxyz12345",
                "organization": "Org1",
                "workgroups": [1, 2, 3]
            }
        ],
        "next": None,
        "start": 0,
        "previous": None
    }
    project2 = {
        "count": 1,
        "num_pages": 1,
        "current_page": 1,
        "results": [
            {
                "id": 2,
                "url": "/api/server/projects/2/",
                "created": "2015-08-04T13:26:01Z", "modified": "2015-08-04T13:26:01Z",
                "course_id": "course1",
                "content_id": "i4x://MyCompany/GP2/gp-v2-project/41fe8cae0614470c9aeb72bd078b0348",
                "organization": None,
                "workgroups": [20, 21, 22]
            }
        ],
        "next": None,
        "start": 0,
        "previous": None
    }
    two_projects = {
        "count": 2,
        "num_pages": 1,
        "current_page": 1,
        "results": [
            {
                "id": 1,
                "url": "/api/server/projects/1/",
                "created": None, "modified": None,
                "course_id": "MyCompany/GP2/T2",
                "content_id": "i4x://MyCompany/GP2/gp-v2-project/abcdefghijklmnopqrstuvwxyz12345",
                "organization": "Org1",
                "workgroups": [1, 2, 3]
            },
            {
                "id": 2,
                "url": "/api/server/projects/2/",
                "created": None, "modified": None,
                "course_id": "MyCompany/GP2/T2",
                "content_id": "i4x://MyCompany/GP2/gp-v2-project/abcdefghijklmnopqrstuvwxyz12346",
                "organization": "Org1",
                "workgroups": [1, 2, 3]
            }

        ],
        "next": None,
        "start": 0,
        "previous": None
    }
    zero_projects = {
        "count": 0,
        "num_pages": 1,
        "current_page": 1,
        "results": [],
        "next": None,
        "start": 0,
        "previous": None
    }


class Workgroups(object):
    workgroup1 = {
        "id": 20,
        "url": "/api/server/workgroups/20/",
        "created": "2015-11-05T12:20:10Z", "modified": "2015-11-13T11:07:58Z",
        "name": "Group 1",
        "project": 2,
        "groups": [
            {
                "id": 54,
                "url": "/api/server/groups/54/",
                "name": "Assignment group for 20",
                "type": "reviewassignment",
                "data": {
                    "xblock_id": "i4x://MyCompany/GP2/gp-v2-activity/ddf65290008d48c991ec41f724877d90",
                    "assignment_date": "2015-11-05T12:45:10.870070Z"
                }
            }
        ],
        "users": [
            {"id": 17, "url": "/user_api/v1/users/17/", "username": "Alice", "email": "Alice@example.com"},
            {"id": 20, "url": "/user_api/v1/users/20/", "username": "Derek", "email": "Derek@example.com"}
        ],
        "submissions": [1, 2, 3],
        "workgroup_reviews": [4, 5, 6],
        "peer_reviews": [7, 8, 9]
    }
    workgroup2 = {
        "id": 21,
        "url": "http://localhost/api/server/workgroups/21/",
        "created": "2015-11-05T12:20:18Z", "modified": "2015-11-05T12:45:13Z",
        "name": "Group 2",
        "project": 1,
        "groups": [
            {
                "id": 55,
                "url": "http://localhost/api/server/groups/55/",
                "name": "Assignment group for 21",
                "type": "reviewassignment",
                "data": {
                    "xblock_id": "i4x://MyCompany/GP2/gp-v2-activity/ddf65290008d48c991ec41f724877d90",
                    "assignment_date": "2015-11-05T12:45:12.563121Z"
                }
            }
        ],
        "users": [
            {"id": 18, "url": "/user_api/v1/users/18/", "username": "Bob", "email": "Bob@example.com"}
        ],
        "submissions": [10, 11],
        "workgroup_reviews": [117, 118, 119, 120, 135],
        "peer_reviews": [1111, 1121, 111011]
    }


class Completions(object):
    non_paged1 = {
        "count": 5,
        "next": None,
        "previous": None,
        "num_pages": 1,
        "results": [
            {
                "id": 306, "user_id": 22, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
            },
            {
                "id": 307, "user_id": 23, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
            {
                "id": 308, "user_id": 24, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
            {
                "id": 309, "user_id": 25, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
            {
                "id": 310, "user_id": 26, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:31:20Z", "modified": "2015-11-17T10:31:20Z"
            },
        ]
    }

    non_paged2 = {
        "count": 5,
        "next": None,
        "previous": None,
        "num_pages": 1,
        "results": [
            {
                "id": 306, "user_id": 22, "course_id": "course1", "stage": None, "content_id": "content2",
                "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
            },
        ]
    }

    empty = {"count": 0, "next": None, "previous": None, "num_pages": 1, "results": []}

    paged_page1 = {
        "count": 3,
        "next": "http://localhost/api/server/courses/course1/completions/?content_id=content1&page=2",
        "previous": None,
        "num_pages": 3,
        "results": [
            {
                "id": 306, "user_id": 22, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
            },
            {
                "id": 307, "user_id": 23, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
            {
                "id": 308, "user_id": 24, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
        ]
    }
    paged_page2 = {
        "count": 3,
        "next": "http://localhost/api/server/courses/course1/completions/?content_id=content1&page=3",
        "previous": "http://localhost/api/server/courses/course1/completions/?content_id=content1&page=1",
        "num_pages": 3,
        "results": [
            {
                "id": 309, "user_id": 25, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
            },
            {
                "id": 310, "user_id": 26, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
            {
                "id": 311, "user_id": 27, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            },
        ]
    }
    paged_page3 = {
        "count": 3,
        "next": None,
        "previous": "http://localhost/api/server/courses/course1/completions/?content_id=content1&3page=23",
        "num_pages": 3,
        "results": [
            {
                "id": 312, "user_id": 28, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:29Z", "modified": "2015-11-17T10:30:29Z"
            },
            {
                "id": 313, "user_id": 29, "course_id": "course1", "stage": None, "content_id": "content1",
                "created": "2015-11-17T10:30:42Z", "modified": "2015-11-17T10:30:42Z"
            }
        ]
    }
