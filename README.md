# xblock-group-project-v2

This XBLock is experimental reimplementation of [Group Project XBlock](https://github.com/edx-solutions/xblock-group-project). 

This group implements a group project, that is: a group of students work together on a task which is then graded.
Project deliverables are defined by course staff, and can be arbitrary files. Project deliverables can be submitted 
by any team member. Group is graded as a whole --- each student gets the same mark for the group project. 

Project can be graded either by staff, or by peers from other groups. Individual performance can be assessed using 
the team evaluation feature where performance of team member is assessed by the rest of their team. 

It does *not* work properly in LMS yet.  

## Features

**Team Evaluations**
 
Workgroup members can provide anonymous feedback to each other.

**Grading**
 
Activities are either peer-graded or staff-graded:

* *Staff grading* - staff members with appropriate roles are asked to provide grade for the workgroup.
* *Peer grading* - students are asked to evaluate other workgroups' work.
* *Staff-grading fallback* - if some of the students fail to provide grades to another workgroup, staff members can 
  interfere and provide missing grades.

**Hierarchical structure**
 
Group projects are organized around activities and stages: 

* Activities are the larger chunks, used to distinguish between different parts of group project. Activities 
  can contain one or more stages. Grading happens at activity level, i.e. each student receive one grade per 
  activity.
* Stages are smaller building blocks, representing individual steps towards project completion.

**Collaborative learning** 

Students are organized into workgroups (aka cohorts) to work on a set of problems in a collaborative way.

**Team communication**
 
Group project interface allows student sending emails to individual teammates or his entire workgroup.

**Private discussions** 

Private (aka cohorted) discussions can be configured for the group project to provide platform for discussing the 
assignments between teammates and avoid revealing the results/ideas to other workgroups or future course students.

**Resources**

Course authors can provide a set of resources - videos or documents - to help orient students, provide deliverable 
templates, or just share some relevant information about the assignment.

**File submissions**

Results of work produced by students are uploaded to the server to facilitate sharing them between team members and 
for future grading.
      
**Omnipresent features**

Group Project Navigator is always displayed and provides quick access to most commonly used features:

* Project navigation - jump to any stage in any activity in one click.
* Resources panel - all the resources in one place.
* Submissions panel - upload, view and change deliverables as you go.
* Private discussions - connect with teammates.
* Ask Teaching Assistant - ask course staff for help in seconds.

## High Level Overview

This is covered in more detail in [the authoring documentation](/docs/authoring.md). 

### Project XBlock 

Top most component of Group Work v2 is Project XBlock. Project XBlock holds a number of activities. 
Workgroups are defined on project level, i.e. the same students are working together thought every activity in 
a given project. Workgroups are not defined inside GroupWorkProject XBlock, currently they must be defined in the 
proprietary Apros management interface, XBlocks belonging to the project query `edx-solutions` api for the workgroups. 

Project XBlock can contain following children:  

* Project navigation XBlock --- this one is strictly necessary, without it this project XBlock doesnt work at all.  
* Private discussion XBlock --- this one is optional, if missing GWv2 will gracefully handle it and just omit 
  private discussions. 
* Some number of Activity XBlocks --- there should be at least one.   

Detailed list of available XBlocks is [available in the docs folder](/docs/XBlocks.md).

### Activity XBlock 

Activity represents a single item of work that the team performs, Grading is done at the activity level: that is 
student will be assigned grades for each activity.

Grade for activity is the same for all students in the group, grades are assigned as part of Peer grading/Staff grading
process. This will be explained in the next section. 

Activity XBlock also contains informational only `Due date` field --- which is displayed to users in the proprietary 
Apros Interface, but doesn't really alter any logic. Hard deadlines are set on Stage level. 


### Stage XBlock 

Stage XBlock represents a single view user sees in the GWv2 project. Stages aren't graded, but completions are 
recorded on stage level. Completions also create progress events, that are used to track and display student progress
inside the proprietary Apros interface. 

Detailed list of available XBlocks is [available in the docs folder](/docs/XBlocks.md), also conditions for a particular
stage to be considered completed are mentioned there for each stage. 

Stage have open and close dates, user's can't interact fully with the stage before `open_date`, and can't submit their 
work after `close_date`. 

### High level description of stages

Detailed list of available XBlocks is [available in the docs folder](/docs/XBlocks.md). 

#### Deliverable stage

Deliverable stage is a stage where students submit output of their work. Work is submitted as a series of upload files. 

#### Grading 

Students are graded by `Peer Grading` stage. Each grading stage contains a list of Review Questions. 

Graders can be asked to either provide a descriptive assessment, or a numerical grade. Numerical grades are used for 
grading workgroup members, while descriptive assessments are purely informational. See this example grading rubric:  

![Grading rubric example](/docs/images/stage_components/review_questions.png)
 
Workgroup is graded as a whole --- each student gets the same mark. 
 
Grading can be done either by course staff (staff-grading), or by other students (peer-grading). 
In peer-grading schema submissions made by workgroup are graded by configurable number of their peers. 

#### Team Evaluation 

Individual performance can be assessed by using `Team Evaluation` stage. In this stage, each student 
is evaluated by the rest of their team. Team evaluations are done anonymously, and displayed to student 
as a part of `Evaluation Display` stage. 

# Development

Short summary: developing on Group Project XBlock v2 and running tests requires, at the minimum:

* python>=2.7,<3.0
* pip>=6.0
* node.js>=0.10
* npm>=1.3.10 (might work with older versions, but not checked)

Other dependencies are installed via `pip install -r requirements/dev.txt` and `npm install`.

Group Project XBlock v2 contains a Makefile to help with most common operations.

Running tests:

* `./run_tests.py` to run all python tests (integration tests are run in actual firefox window)
* `xvfb-run --server-args="-screen 0, 1920x1080x24" ./run_tests.py` - runs all python tests in virtual X server.
* `./node_modules/.bin/karma start tests/js/karma.conf.js` - run JS tests in continuous mode (stays open, 
    watches file changes, re-runs the suite on file change)
* `./node_modules/.bin/karma start tests/js/karma.conf.js --single-run` - run JS tests once.
    
Checking quality violations: `make quality` to check everything. Fails fast, might not display all violations - make 
sure to achieve clean pass.

Refer to [development documentation][dev-docs] for more details.

# Additional in-depth documentation

1. [Authoring][authoring]
2. [Information on development][dev-docs]
3. [Deployment information][deployment]

[authoring]: /docs/authoring.md
[dev-docs]: /docs/development.md
[deployment]: /docs/deployment.md
