# Group Project XBlock Xml Schema Information

## `<group_project>`
Top level node

### Attributes
`schema_version` _Optional - currently supporting only the value '1' while under development_

### Child Nodes
`resources` _Optional_

`submissions` _Optional_

`dates` _Optional_

`projectcomponent` _Required_

## `<resources>`
Node defining which external resources (authored by instructor or others) provide useful information about the project

### Attributes
_None_

### Child Nodes
`document` _Required_

## `<submissions>`
Node defining which documents are required to be uploaded by the group in order to complete the project

### Attributes
_None_

### Child Nodes
`document` _Required_

## `<dates>`
Node highlighting the important dates for this project

### Attributes
_None_

### Child Nodes
`milestone` _Required_

## `<projectcomponent>`
Node defining a stage for a group project

### Attributes
`name` _Required - Stage Name: This is displayed as the name of the item within the application_

`id` _Required - Stage id: This is used to uniquely identify the stage_

`open` _Optional - Refers to a milestone date defined within `dates`. This is considered the date at which this content is available to be viewed by the end user_

`close` _Optional - Refers to a milestone date defined within `dates`. This is considered the date at which this content is considered to be closed, and will accept no more input_

### Child Nodes
`section` _Optional - Defines a section within the page_

`peerreview` _Optional - Wrapper around `section` nodes that are designed to be shown for peer review_

`projectreview` _Optional - Wrapper around `section` nodes that are designed to be shown for project review_

`peerassessment` _Optional - Wrapper around `section` nodes that are designed to be shown for peer assessment_

`projectassessment` _Optional - Wrapper around `section` nodes that are designed to be shown for project assessment_

## `<document>`
A document definition, for either an existing document or a document to be provided by the group

### Attributes
`title` _Required - Title of document_

`description` _Optional - Description of document_

`grading_criteria` _Optional - a value of "true" indicates that this document is also considered to hold information about the criteria used to grade the project_

### Child Nodes
Content represents the url from which the document may be downloaded. Note that submissions documents will have not text content

## `<milestone>`
Node defining a significant date during the course of running the group project

### Attributes
`name` _Required - Name of the milestone that this date represents_

### Child Nodes
Content represents the milestone date _Using the US format of m/d/y_

## `<section>`
Node describing content to display within the page

### Attributes
`title` _Optional - Title to display above the section within the browser_

`file_links` *Optional - file links to display after the section content has been displayed: value is one of `resources`, `submissions` or `grading_criteria` (Note that `resources` include grading criteria, and `grading_criteria` displays only the resource(s) that is marked as such)*

### Child Nodes
`content` _Optional - contains HTML to include within the document (Note that XHTML syntax should be used to allow Xml document to be validated as Xml)_

`question` _Optional - question to ask for review target (only valid within peerreview and projectreview nodes_

`assessment` _Optional - location to show review results from feedback_

## `<peerreview>`
Node to define sections to be associated with specific peer selection
**Note that it is important to provide a node with class "peers" in a section/content node within the same projectcomponent, but outside of the scope of this peerreview node - this node is injected with the peers within the user's group**

### Attributes
None

### Child Nodes
`section` - _Required - section(s) to display peer review questions_

## `<projectreview>`
Node to define sections to be associated with specific group review selection 
**Note that it is important to provide a node with class "other_groups" in a section/content node within the same projectcomponent, but outside of the scope of this projectreview node - this node is injected with the groups for whom the user has been chosen to provide feedback**

### Attributes
None

### Child Nodes
`section` - _Required - section(s) to display project review questions_

## `<peerassessment>`
Node to define sections to display the feedback that the user has recieved from her/his peers.
**Note that it is important to provide a link with the following definition in a section/content node within the same projectcomponent, but outside of the scope of this peerassessment node - this link tells the xblock to show/hide the peer assessments (_You can provide custom content_):**
    
    <a data-showid="team_feedback" class="view_feedback">Team Feedback</a>

### Attributes
None

### Child Nodes
`section` - _Required - section(s) to display peer review assessments from others_

## `<projectassessment>`
Node to define sections to display the feedback that the group has recieved from others about their project.
**Note that it is important to provide a link with the following definition in a section/content node within the same projectcomponent, but outside of the scope of this projectassessment node - this link tells the xblock to show/hide the project assessments (_You can provide custom content_):**
    
    <a data-showid="cohort_feedback" class="view_feedback">Cohort Feedback</a>

### Attributes
None

### Child Nodes
`section` - _Required - section(s) to display peer review assessments from others_

## `<content>`
Node to contain HTML content to be displayed within the page

### Attributes
None

### Child Nodes
Content contains HTML - _Note that XHTML syntax will ensure that xml document validation passes_

## `<question>`
Node to represent a question to be asked of a peer or of anohter groups' project

### Attributes
`id` - _Required - small string stored alongside answer data_

`required` - _Optional - any value other than `true` will render the question as not required (default value is `true`)_

### Child Nodes
`label` - _Required - Text (html) for the question being asked_

`answer` - _Required - HTML for form element in which to collect information_

## `<assessment>`
Node for user to see the feedback given from peers and project reviewers

### Attributes
`id` _Required - Must match id of question prefixed with `assess_`_

### Child Nodes
`label` - _Required - Text (html) for the question that was asked_

`answer` - _Required - HTML in which to inject data_
