# Authoring

Group Project XBlock v2 relies heavily on "nested XBlocks". In other words, a Group Project is built from several
XBlocks that work together, each implementing a small subset of the overall Group project functionality: peer grading,
submissions upload, team discussions, etc. Most of these features are implemented with XBlocks that are unique to the
Group Project XBlock v2 package, but some more advanced features reuse other XBlocks from the Open edX ecosystem.

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

A typical Group Project contains several activities, each of which has multiple stages. In addition to that, the
"Project Navigator" is a required component; if it is omitted, the Group Project XBlock will display validation errors 
in Studio and will display an error message in the LMS. Also, Navigation View is a required component of Project
Navigator. Thus, each Group Project XBlock must always contain at least Project Navigator with Navigation View in it.

Activities act as larger chunks of group project by combining stages into logically bound units. Grading 
happens at the activity level.

Each stage represents single group project step - getting acquainted with the team, familiarizing with the task, 
uploading deliverable, providing and receiving grading, etc. Stages themselves are usually built from multiple stage
components - which range from simple HTML blocks to more sophisticated Project Team and Submission blocks. Also, by
using Resource blocks, a stage can provide various resources to the student: grading rubrics, submission templates, or
any other relevant documents and videos.

In the example above, a Group Project with two activities, the Project Navigator and Private Discussions are shown.
Activity 1 is composed of three stages, and Activity 2 is composed of two stages. Some stages have stage components -
even smaller building blocks, varied by stage type. The Project Navigator shown in this example has four nested
XBlocks, which represent most of the child blocks that can be enabled within the Project Navigator.
 
Available stages and their intended use:
 
* `Text` - simple stage showing some author-defined text.
* `Completion` - almost the same as `Text`, except it requires student to explicitly mark this stage as completed. Use
     for simple non-graded tasks, i.e. "Get acquainted with the team", "Read related chapters in course textbook", etc. 
* `Submission` - at this stage students are asked to upload their deliverables. Most of the actual group project work is
   likely to happen during this stage. Use to set up a list of deliverables for an activity and a deadline to upload 
   them. If deliverable templates are provided to students, the best place to place them is in a stage of this type.
* `Team Evaluation` - allows students to provide anonymous feedback to teammates. Intended use is to allow students
    in the team to provide and receive feedback about their team work, role in the team, communication skills, etc.
* `Peer Grading` - this stage, in addition to the `Submission` stage, forms a backbone of group project. During this stage
    deliverables uploaded earlier are graded by either students in other groups or by Teaching Assistants. The grading
    criteria can be delivered to students as contents of this stage or resources on this stage.
* `Evaluation Display` - this stage allows students to review feedback from their teammates. Use with `Team Evaluation` stage.
* `Grade Display` - this stage allows students to review their group grade and feedback received from graders. Use with 
    `Peer Grading` stage.

For more information, see [the detailed list of available XBlocks](/docs/XBlocks.md).

Group Project XBlock v2 uses standard Studio editing capabilities:

<img src="/docs/images/studio_edit1.png" width="400" alt='Studio screenshot displaying project navigator XBlock, with outlined "View" (red outline) and "Edit" (blue outline) buttons'>

* The Edit button (blue outline) is used to edit XBlock settings, i.e. "Display name", "Open Date", "Close Date", etc.
* The View button (red outline) allows to "jump into" an XBlock and view its nested XBlocks, allowing to add,
    configure, reorder and delete them.

This screenshot shows the same Group Project Navigator XBlock "from the inside", displaying Project Navigator Views
added to the navigator. 

<img src="/docs/images/studio_edit2.png" width="400" aria-hidden="true">
