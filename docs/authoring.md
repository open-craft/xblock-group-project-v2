# Authoring

Group Project XBlock v2 relies heavily on "nested XBlocks" feature, provided by edX Platform and XBlocks ecosystem.
To be precise, Group Project is built from smaller XBlocks, each implementing some smaller subset of Group project 
functionality: peer grading, submissions upload, team discussions, etc. Most of these features are internal to Group 
Project XBlock v2 package, but some more advanced features reuse other XBlocks.

An example of a Group Project containing two activities: 

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
building blocks, varied by stage type. Project Navigator includes most of the child blocks that are available for it.

Typical Group Project contains several activities, each of which has multiple stages. In addition to that,
Group Project Navigator is a required component, so if it is omitted Group Project XBlock will display validation errors 
in Studio and will display an error message in LMS and Apros. Also, Navigation View is a required component of Project
Navigator, so any correct Group Project XBlock will contain at least Project Navigator with Navigation View in it.

Activities act as larger chunks of group project by combining stages into logically bound units. Grading 
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
    in the team to provide and receive feedback about their team work, role in the team, communication skills, etc.
* `Peer Grading` - this stage, in addition to `Submission` stage forms a backbone of group project. During this stage
    deliverables uploaded earlier are graded by either students in other groups or Teaching Assistants. Grading criteria
    can be delivered to students as contents of this stage or resources on this stage.
* `Evaluation Display` - this stage allows students to review feedback from their teammates. Use with `Team Evaluation` stage.
* `Grade Display` - this stage allows students to review their group grade and feedback received from graders. Use with 
    `Peer Grading` stage.

Detailed list of available XBlocks is [available in the docs folder](/docs/XBlocks.md).

Group Project XBlock v2 uses standard Studio editing capabilities:

<img src="/docs/images/studio_edit1.png" width="400" alt="Studio screenshot displaying project navigator XBlock, with outlined "View" (red outline) and "Edit" (blue outline) buttons">

* Edit button (blue outline) is used to edit XBlock settings, i.e. "Display name", "Open Date", "Close Date", etc.
* View button (red outline) allows to "jump into" an XBlock and view it's nested XBlocks, allowing to add, configure, 
    reorder and delete them.

This screenshot shows the same Group Project Navigator XBlock "from the inside", displaying Project Navigator Views
added to the navigator. 

<img src="/docs/images/studio_edit2.png" width="400" aria-hidden="true">

