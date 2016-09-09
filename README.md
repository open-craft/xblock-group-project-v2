# xblock-group-project-v2

This set of XBLocks is an experimental reimplementation of [Group Project XBlock](https://github.com/edx-solutions/xblock-group-project). 

This tool implements a group project, where a group of students work together on a task, which is then graded.
Project deliverables are defined by course staff, and can be arbitrary files. Project deliverables can be submitted 
by any group member. Each group is graded as a whole -- each student gets the same mark for the group project. 

A group project can be graded either by staff, or by peers from other groups. Individual performance can be assessed
using the group evaluation feature where performance of each group member is assessed by the rest of their group. 

It does *not* work properly in the official Open edX LMS platform yet.


## Features

**Team Evaluations**
 
Workgroup members can provide anonymous feedback to each other.

**Grading**
 
Activities are either peer-graded or staff-graded:

* *Staff grading* - staff members with appropriate roles are asked to provide grade for the workgroup.
* *Peer grading* - students are asked to evaluate other workgroups' work.
* *Staff-grading fallback* - if some of the students fail to provide grades to another workgroup, staff members can 
  intervene and provide missing grades.

**Hierarchical structure**
 
Group projects are organized around activities and stages: 

* Activities are the larger chunks, used to distinguish different parts of group project. Activities can contain one
  or more stages. Grading happens at the activity level, i.e. each student receive one grade per activity.
* Stages are smaller building blocks, representing individual steps towards project completion.

**Collaborative learning** 

Students are organized into workgroups (aka cohorts) to work on a set of problems in a collaborative way.

**Team communication**
 
The group project interface allows students to send emails to other individual group members or the entire group.

**Private discussions** 

Private (aka cohorted) discussions can be configured for the group project to provide a platform for discussing the 
assignments among teammates and avoid revealing the results/ideas to other workgroups or future course students.

**Resources**

Course authors can provide a set of resources - videos or documents - to help orient students, provide deliverable 
templates, or just share some relevant information about the assignment.

**File submissions**

The results of work produced by students are uploaded to the server to facilitate sharing them among team members
and for future grading.

**Admin Dashboard**

Admin dashboard provides course staff with information about student progress through the problem - both at workgroup
and individual level. Detailed information available in the [admin dashboard documentation](/docs/admin_dashboard.md). 
      
**Omnipresent features**

The Group Project Navigator is always displayed and provides quick access to the most commonly used features:

* Project navigation - jump to any stage in any activity in one click.
* Resources panel - all the resources in one place.
* Submissions panel - upload, view and change deliverables as you go.
* Private discussions - connect with teammates.
* Ask Teaching Assistant - ask course staff for help in seconds.

## High Level Overview

This is covered in more detail in [the authoring documentation](/docs/authoring.md), and a detailed list of available
group project XBlocks is [available in the docs folder](/docs/XBlocks.md).

### Project XBlock 

The top most component of Group Work v2 is the Project XBlock. The Project XBlock holds a number of activities. 
Workgroups are defined on project level, i.e. the same group of students will work together for every activity in 
a given project. Workgroups are not defined inside the Project XBlock; currently they must be defined in the 
proprietary Apros management interface. The Project XBlock and other XBlocks that comprise Group Work v2 retrieve
the group assignments by querying an API found only on the `edx-solutions` fork of edx-platform.

The Project XBlock can contain following children:  

* Project Navigation XBlock --- this one is strictly necessary; without it this project XBlock doesn't work at all.  
* Private Discussion XBlock --- this one is optional; if missing GWv2 omit private discussions. 
* Some number of Activity XBlocks --- there should be at least one.   

### Activity XBlock 

An Activity represents a single item of work that the team performs. Grading is done at the activity level; that is,
each group will be assigned a grade for each activity.

The grade earned for an activity is the same for all students in the group. Grades are assigned during the Peer
grading/Staff grading process. This will be explained in the next section. 

An Activity XBlock also contains a `Due date` field --- which is displayed to users in the proprietary 
Apros Interface, but is considered advisory only as it doesn't affect any logic or grading. Hard deadlines are set at
the Stage level. 


### Stage XBlocks

A Stage XBlock represents a single view that the student will see in the GWv2 project. Stages aren't graded, but
completion of each stage is recorded by the system. Completions also create progress events, that are used to track and
display student progress, if supported by the LMS. 

Each Stage has open and close dates. Students cannot interact fully with the stage before the `open_date`, and cannot
submit their work after the `close_date`. 

See the [XBlock details available in the docs folder](/docs/XBlocks.md), for details on each available stage type, and
the conditions required for a particular stage to be considered complete.

#### Deliverable Stage

A Deliverable Stage is a stage where students submit the output of their work. Work is submitted as a series of
one or more uploaded files.

#### Grading 

Students are graded during the `Peer Grading` stage. Each grading stage contains a list of Review Questions. 

Graders can be asked to either provide a descriptive assessment, or a numerical grade. Numerical grades are used for 
grading workgroup members, while descriptive assessments are purely informational. See this example grading rubric:  

![Grading rubric example](/docs/images/stage_components/review_questions.png)
 
Each group is graded as a whole --- each student gets the same mark. 
 
Grading can be done either by course staff (staff-grading), or by other students (peer-grading). 
In peer-grading, submissions made by the group are graded by a configurable number of their peers. 

#### Team Evaluation 

Individual performance can be assessed by using the Team Evaluation stage. In this stage, each student
is evaluated by the rest of their team. Team evaluations are done anonymously, and displayed to the student
in an Evaluation Display stage. 

# Development

Developing with Group Project XBlock v2 and running the test suite requires, at the minimum:

* python>=2.7,<3.0
* pip>=6.0
* node.js>=0.10
* npm>=1.3.10 (might work with older versions, but not checked)

Other dependencies are installed via `pip install -r requirements/dev.txt` and `npm install`.

Group Project XBlock v2 contains a Makefile to help with most common operations.

Running tests:

* `./run_tests.py` to run all python tests (integration tests are run in a Firefox window)
* `xvfb-run --server-args="-screen 0, 1920x1080x24" ./run_tests.py` - runs all python tests in virtual X server.
* `./node_modules/.bin/karma start tests/js/karma.conf.js` - run JS tests in continuous mode (stays open, 
    watches file changes, re-runs the suite on file change)
* `./node_modules/.bin/karma start tests/js/karma.conf.js --single-run` - run JS tests once.
    
Checking quality violations: `make quality` to check everything. Fails fast, so might not display all violations - make
sure to achieve a clean pass.

Refer to [development documentation][dev-docs] for more details.

# Additional in-depth documentation

1. [Authoring][authoring]
2. [Admin Dashboard][admin-dashboard]
3. [Deployment information][deployment]
4. [Information on development][dev-docs]
5. [XBlocks in this package][xblocks-docs]

[authoring]: /docs/authoring.md
[admin-dashboard]: /docs/admin-dashboard.md
[deployment]: /docs/deployment.md
[dev-docs]: /docs/development.md
[xblocks-docs]: /docs/XBlocks.md
