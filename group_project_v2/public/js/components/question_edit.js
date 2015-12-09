/* globals CodeMirror, StudioEditableXBlockMixin */
/* exported GroupProjectQuestionEdit */
function GroupProjectQuestionEdit(runtime, element) {
    "use strict";
    StudioEditableXBlockMixin(runtime, element);
    var CodeMirrorAvailable = (typeof CodeMirror !== 'undefined'); // Studio includes CodeMirror
    var xmlEditorTextarea = $('div.wrapper-comp-setting [data-field-name="question_content"]', element)[0];

    if (CodeMirrorAvailable) {
        var cm = CodeMirror.fromTextArea(xmlEditorTextarea, {mode: 'xml', lineWrapping: true});

        // TODO: This is a workaround to update the textarea as StudioEditableXBlockMixin will be looking for value
        // there. StudioEditableXBlockMixin should probably provide CodeMirror integration
        // jshint unused:vars
        cm.on("change", function(instance, changeObj) {
            $(xmlEditorTextarea).val(instance.getValue());
            $(xmlEditorTextarea).trigger('change');
        });
        // jshint unused:true
    }
}
