var groupProject = (function() {
	'use strict';

	var _fn = {

		// DOM Elements
		$block: $('.xblock--group-project'),

		// item template
		tpl: {
			array: {
				init: function() {
					var question,
						section;

					_fn.tpl.document = _fn.tpl.array.document();
					_fn.tpl.milestone = _fn.tpl.array.milestone();
					_fn.tpl.elementSelect = _fn.tpl.array.elementSelect();
					_fn.tpl.answerOption = _fn.tpl.array.answerOption();

					// Questions and Assessments
					question = _fn.tpl.array.question();
					_fn.tpl.question = _.template( question, {
						classList: 'question',
						title: 'Question'
					});
					_fn.tpl.assessment = _.template( question, {
						classList: 'assessment',
						title: 'Assessment'
					});

					// Links to add Questions and Assessments
					_fn.tpl.add.question = _.template( _fn.tpl.add.child, {
						type: 'question',
						text: 'Add a Question'
					});
					_fn.tpl.add.assessment = _.template( _fn.tpl.add.child, {
						type: 'assessment',
						text: 'Add an Assessment'
					});

					// The 5 section types
					section = _fn.tpl.array.section();
					_fn.tpl.section = _.template( section, {
						node: 'section',
						title: 'Section',
						footer: '<footer class="section-footer"></footer>'
					});
					_fn.tpl.peerreview = _.template( section, {
						node: 'peerreview',
						title: 'Peer Review',
						footer: _fn.tpl.add.question
					});
					_fn.tpl.projectreview = _.template( section, {
						node: 'projectreview',
						title: 'Project Review',
						footer: _fn.tpl.add.question
					});
					_fn.tpl.peerassessment = _.template( section, {
						node: 'peerassessment',
						title: 'Peer Assessment',
						footer: _fn.tpl.add.assessment
					});
					_fn.tpl.projectassessment = _.template( section, {
						node: 'projectassessment',
						title: 'Project Assessment',
						footer: _fn.tpl.add.assessment
					});
				},
				answerOption: function() {
					return [
						'<div class="option-wrapper">',
							'<input type="text" class="answer-option <%= classList %>" />',
							'<a href="#" class="remove-element" data-element="option-wrapper">',
								'<div class="icon remove"></div>',
							'</a>',
						'</div>'
					].join('');
				},
				document: function() {
					return [
						'<div class="document">',
							'<div class="row">',
								'<label>Title</label>',
		                        '<input type="text" class="title" />',
		                        '<label>Url</label>',
		                        '<input type="text" class="url" />',
		                        '<label>Grading Criteria</label>',
		                        '<select class="grading-criteria">',
		                            '<option value="false">False</option>',
		                            '<option value="true">True</option>',
		                        '</select>',
		                        '<a href="#" class="remove-element hidden" data-element="document">',
									'<div class="icon remove"></div>',
								'</a>',
		                    '</div>',
		                    '<div class="row">',
		                        '<textarea class="description"></textarea>',
		                    '</div>',
		                '</div>',
					].join('');
				},
				elementSelect: function() {
					return [
						'<select class="answer-element">',
                            '<option value="false">Please select an element...</option>',
                            '<option value="text">Text field</option>',
                            '<option value="textarea">Textarea</option>',
                            '<option value="radio">Radio Button</option>',
                            '<option value="checkbox">Checkbox</option>',
                            '<option value="select">Dropdown</option>',
                        '</select>'
					].join('');
				},
				question: function() {
					return [
						'<section class="<%= classList %>">',
                            '<h3><%= title %></h3>',
                            '<a href="#" class="remove-element" data-element="<%= classList %>">',
								'<div class="icon remove"></div>',
							'</a>',
							'<label>ID</label>',
                            '<input type="text" class="id" />',
							'<label>Label</label>',
                            '<input type="text" class="label" />',
                            _fn.tpl.elementSelect,
                            '<div class="answer-options hidden">',
                                '<label>Answer Options</label>',
                                '<div class="option-wrapper">',
                                	'<input type="text" class="answer-option answer-1" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
								'<div class="option-wrapper">',
                                	'<input type="text" class="answer-option answer-2" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
								'<div class="option-wrapper">',
	                                '<input type="text" class="answer-option answer-3" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
								'<div class="option-wrapper">',
	                                '<input type="text" class="answer-option answer-4" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
								'<div class="option-wrapper">',
	                                '<input type="text" class="answer-option answer-5" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
								'<div class="option-wrapper">',
	                                '<input type="text" class="answer-option answer-6" />',
	                                '<a href="#" class="remove-element" data-element="option-wrapper">',
										'<div class="icon remove"></div>',
									'</a>',
								'</div>',
                                '<a href="#" class="add-element" data-add="answer"><div class="icon add"></div>Add an answer option</a>',
                            '</div>',
                        '</section>'
					].join('');
				},
				milestone: function() {
					return [
						'<div class="milestone">',
							'<label>Name</label>',
	                        '<input type="text" class="name" />',
	                        '<label>Date</label>',
	                        '<input type="text" class="date" placeholder="m/d/yyyy" />',
	                        '<a href="#" class="remove-element hidden" data-element="milestone">',
								'<div class="icon remove"></div>',
							'</a>',
	                    '</div>'
					].join('');
				},
				section: function() {
					return [
						'<section class="section" data-node="<%= node %>">',
                            '<header class="section-header">',
                            	'<h2><%= title %></h2>',
	                            '<a href="#" class="remove-element" data-element="section">',
									'<div class="icon remove"></div>',
								'</a>',
                            '</header>',
                            '<div class="row">',
                                '<label>Title</label>',
                                '<input type="text" class="title" />',
                                '<label>File Links</label>',
                                '<select class="file-links">',
                                    '<option value="false">Select links to display...</option>',
                                    '<option value="resources">Resources</option>',
                                    '<option value="submissions">Submissions</option>',
                                    '<option value="grading-criteria">Grading Criteria</option>',
                                '</select>',
                            '</div>',
                            '<div class="row">',
                                '<textarea class="content" placeholder="Content"></textarea>',
                            '</div>',
                        	'<footer class="section-footer">',
                            	'<%= footer %>',
                        	'</footer>',
                        '</section>'
					].join('');
				}
			},
			label: '<label class="<%= classList %>"><%= title %></label>',
			option: '<option value="<%= value %>"><%= title %></option>',
			textfield: '<input type="text" class="<%= classList %>" />',
			item: '<li class="option" data-value="<%= id %>"><%= displayName %></li>',
			submission: '<div class="row"><input type="text" placeholder="Name" /></div>',
			add: {
				assessment: '',
				question: '',
				child: '<a href="#" class="add-element" data-add="<%= type %>"><div class="icon add"></div><%= text %></a>'
			},
			answerOption: '',
			assessment: '',
			document: '',
			elementSelect: '',
			milestone: '',
			question: '',
			section: '',
			peerreview: '',
			projectreview: ''
		},

		build: {
			$el: {
				general: $('.xblock--group-project .general-form'),
				overview: $('.xblock--group-project .overview-form')
			},
			dropdown: {
				date: ''
			},
			datepicker: {
				loaded: false,
				options: [],
				add: function() {
					var $form = _fn.$block.find('form'),
						$attributes = $form.find('.attributes'),
						dates = _fn.data.dates,
						dropdownDates = [],
						datesEntered = dates.length > 0;

					if ( datesEntered ) {
						_.each(dates, function(el) {
							if ( el.name.length > 0 && el.date.length > 0 ) {
								dropdownDates.push({
									title: el.name,
									value: el.name
								});
							}
						});

						dropdownDates.unshift({
							title: 'Select a milestone',
							value: 'false'
						});

						$attributes.append(
							_fn.build.form.create.milestoneSelect( dropdownDates, 'open' ),
							_fn.build.form.create.milestoneSelect( dropdownDates, 'close' )
						);

						_fn.build.datepicker.options = _.pluck( dates, 'name' );
					}

					return datesEntered;
				},
				set: function() {
					var datepicker = _fn.build.datepicker;

					if ( datepicker.loaded ) {
						datepicker.update();
					} else {
						datepicker.loaded = datepicker.add();
					}
				},
				update: function() {
					var currentOptions = _fn.build.datepicker.options,
						newOptions =  _.pluck( _fn.data.dates, 'name' ),
						i,
						newLength = newOptions.length,
						html = [],
						tpl = _fn.tpl.option;
console.log('update ', newLength, ' vs ', currentOptions.length);
					// compare these 2 arrays
					if ( newLength > currentOptions.length ) {
						for ( i = 0; i < newLength; i++ ) {
console.log(i);
							if ( $.inArray( newOptions[i], currentOptions) === -1 ) {
								html.push( _.template( tpl, {
									title: newOptions[i],
									value: newOptions[i]
								}));
							}
						}

						_fn.build.datepicker.options = newOptions;
console.log('html ', html);
						// Will only allow users to add more options
						// so can just append to the end of current dropdowns
						$('.milestone-select').append( html.join('') );
					} else {
console.log('fail');
                    }
				}
			},
			init: function() {
				var $form = _fn.build.$el.general;

				_fn.tpl.array.init();

				// Add default form elements to the DOM
                $form.find('.resources .add-element').before( _fn.tpl.document );
				$form.find('.submissions .add-element').before( _fn.tpl.document );
				$form.find('.dates .add-element').before( _fn.tpl.milestone );

				_fn.utils.texteditor.init( $form.find('textarea') );
				_fn.utils.tabs.init();
				_fn.build.eventHandlers.init();
				_fn.utils.datepicker.init( $('.date') );

				$.placeholder.shim();
			},
			eventHandlers: {
				init: function() {
					_fn.build.eventHandlers.click();
					_fn.build.eventHandlers.change();
				},
				click: function() {
					_fn.$block.on( 'click', '.add-element', _fn.build.form.add.handler );
					_fn.$block.on( 'click', '.remove-element', _fn.build.form.remove.element );
					_fn.$block.on( 'click', '.goto-tab', _fn.build.submit.tab );
					_fn.$block.on( 'click', '.submit', _fn.build.submit.project );
				},
				change: function() {
					_fn.$block.on( 'change', '.add-child', function(e) {
						var $el = $(e.currentTarget),
							child = $el.val();

						if ( child !== 'false') {
							_fn.build.form.create[child]( $el.closest('footer') );
						}
					});
					_fn.$block.on( 'change', '.answer-element', _fn.build.form.update.answer );
				}
			},
			form: {
				get: {
					componentData: function( $form ) {
						var $attr = $form.find('.attributes'),
						    section = _fn.build.form.get.sectionData( $form, 'section' ),
						    name = $attr.find('.name').val(),
						    id = $attr.find('.id').val(),
						    obj = {},
						    peer = {},
						    project = {};

						if ( name.length > 0 && id.length > 0 ) {
						    peer = {
						    	review: _fn.build.form.get.sectionData( $form, 'peerreview' ),
						    	assessment: _fn.build.form.get.sectionData( $form, 'peerassessment' )
						    };

						    project = {
						    	review: _fn.build.form.get.sectionData( $form, 'projectreview' ),
						    	assessment: _fn.build.form.get.sectionData( $form, 'projectassessment' )
						    };

							obj = {
								name: name,
								id: id,
								open: $attr.find('.open').val(),
								close: $attr.find('.close').val()
							};

							if ( section.length > 0 ) { obj.section = section; }
							if ( peer.review.length > 0 ) { obj.peerreview = peer.review; }
							if ( peer.assessment.length > 0 ) { obj.peerassessment = peer.assessment; }
							if ( project.review.length > 0 ) { obj.projectreview = project.review; }
							if ( project.assessment.length > 0 ) { obj.projectassessment = project.assessment; }
						}

						return obj;
					},
					documentData: function( $container ) {
						var $docs = $container.find('div.document'),
							data = [];

						$docs.each( function(i, el) {
							var $el = $(el),
								title = $el.find('.title').val();

							if ( title.length > 0 )	{
								data.push({
									title: title,
									url: $el.find('.url').val(),
									description: _fn.utils.texteditor.getContent( $el.find('.description') ),
									grading_criteria: $el.find('.grading-criteria').val()
								});
							}
						});

						return data;
					},
					milestoneData: function( $container ) {
						var $docs = $container.find('div.milestone'),
							data = [];

						$docs.each( function(i, el) {
							var $el = $(el),
								$name = $el.find('.name'),
								name = $name.val(),
								date = $el.find('.date').val();

							if ( name.length > 0 && date.length > 0 ) {
								data.push({
									name: name,
									date: date
								});

								// Disable name field so user cannot update/delete
								$name.attr('disabled', true);
								$el.find('.remove-element').detach();
							}
						});

						return data;
					},
					questionData: function( $questions ) {
						var data = [];

						$questions.each( function( i, el ) {
							var $el = $(el),
								id = $el.find('.id').val();

							if ( id.length > 0 ) {
								data.push({
									id: id,
									label: $el.find('.label').val(),
									answer: _fn.build.form.get.answerData( $el )
								});
							}
						});

						return data;
					},
					answerData: function( $container ) {
						var type = $container.find('.answer-element').val(),
							$answers = $container.children('.answer-options').find('.answer-option'),
							obj = {
								type: type
							},
							data = [];

						if ( type === 'radio' || type === 'checkbox' || type === 'select' ) {
							$answers.each( function( i, el ) {
								var val = $(el).val();

								if ( val.length > 0 ) {
									data.push( val );
								}
							});

							obj.options = data;
						}

						return obj;
					},
					sectionData: function( $container, node ) {
						var $sections = $container.find('section.section[data-node=' + node + ']'),
							data = [];

						$sections.each( function(i, el) {
							var $el = $(el),
								title = $el.find('.title').val(),
								questionData = [],
								assessmentData = [],
								obj = {};

							if ( title.length > 0 ) {
								questionData = _fn.build.form.get.questionData( $el.find('section.question') );
								assessmentData = _fn.build.form.get.questionData( $el.find('section.assessment') );

								obj = {
									title: title,
									file_links: $el.find('.file-links').val(),
									content: _fn.utils.texteditor.getContent( $el.find('.content') )
								};

								if ( questionData.length > 0 ) {
									obj.question = questionData;
								}

								if ( assessmentData.length > 0 ) {
									obj.assessment = assessmentData;
								}

								data.push(obj);
							}
						});

						return data;
					}
				},
				create: {
					answer: function( $el ) {
						var $title = $el.children('.answer-options').find('h4'),
							i,
							html = [];

						for ( i=0; i<6; i++ ) {
							html.push(
								_.template( _fn.tpl.textfield, { classList: 'answer-option answer-' + (i + 1) } )
							);
						}

						$title.after( html.join('') );
					},
					dropdown: function( array, classlist ) {
						var dropdown = ['<select class="', classlist, '">'],
							i,
							len = array.length,
							tpl = _fn.tpl.option;

						for ( i=0; i<len; i++ ) {
							dropdown.push( _.template( tpl, array[i] ) );
						}

						dropdown.push('</select>');

						return dropdown.join('');
					},
					label: function( classList, text ) {
						return _.template( _fn.tpl.label, {
							classList: classList,
							title: text
						});
					},
					milestoneSelect: function( array, type ) {
						var text = type.charAt(0).toUpperCase() + type.substring(1),
							classList = type + '-label',
							label = _fn.build.form.create.label( classList, text ),
							select = _fn.build.form.create.dropdown( array, type + ' milestone-select');

						return label + select;
					},
					peerassessment: function( $el ) {
						$el.before( _fn.tpl.peerassessment );
						_fn.utils.texteditor.init( $el.prev('.section[data-node=peerassessment]').find('textarea') );
						_fn.build.form.reset.dropdown( $el.find('.add-child') );
					},
					peerreview: function( $el ) {
						$el.before( _fn.tpl.peerreview );
						_fn.utils.texteditor.init( $el.prev('.section[data-node=peerreview]').find('textarea') );
						_fn.build.form.reset.dropdown( $el.find('.add-child') );
					},
					projectassessment: function( $el ) {
						$el.before( _fn.tpl.projectassessment );
						_fn.utils.texteditor.init( $el.prev('.section[data-node=projectassessment]').find('textarea') );
						_fn.build.form.reset.dropdown( $el.find('.add-child') );
					},
					projectreview: function( $el ) {
						$el.before( _fn.tpl.projectreview );
						_fn.utils.texteditor.init( $el.prev('.section[data-node=projectreview]').find('textarea') );
						_fn.build.form.reset.dropdown( $el.find('.add-child') );
					},
					question: function( $el ) {
						$el.before( _fn.tpl.question );
					},
					section: function( $el ) {
						$el.before( _fn.tpl.section  );
						_fn.utils.texteditor.init( $el.prev('.section[data-node=section]').find('textarea') );
						_fn.build.form.reset.dropdown( $el.find('.add-child') );
					}
				},
				add: {
					answer: function( e ) {
						var $btn = $(e.currentTarget),
							$row = $btn.parent('.answer-options'),
							count = $row.find('.answer-option').length,
							html = _.template( _fn.tpl.answerOption, {
								classList: 'answer-' + ( count + 1 )}
							);

						e.preventDefault();
						$btn.before( html );
						$row.find('.remove-element').removeClass('hidden');
					},
					document: function( e ) {
						var $btn = $(e.currentTarget),
							$row = $btn.prev('.document');

						e.preventDefault();
						$row.after( _fn.tpl.document );
						_fn.utils.texteditor.init( $row.next('.document').find('textarea') );
						$btn.siblings('.document').find('.remove-element').removeClass('hidden');
					},
					handler: function( e ) {
						var $el = $(e.currentTarget),
							block = $el.data('add');

						if 	( block === 'answer' || block === 'document' || block === 'milestone') {
							_fn.build.form.add[block]( e );
						} else if ( block === 'question' || block === 'assessment' ) {
							_fn.build.form.add.question( e, block );
						}
					},
					milestone: function( e ) {
						var $btn = $(e.currentTarget),
							$row = $btn.prev('.milestone');

						e.preventDefault();
						$row.after( _fn.tpl.milestone );
						$btn.siblings('.milestone').children('.remove-element').removeClass('hidden');

						_fn.utils.datepicker.init( $('.date') );
						$.placeholder.shim();
					},
					question: function( e, type ) {
						var $btn = $(e.currentTarget),
							$wrapper = $btn.parent();

						e.preventDefault();
						$wrapper.before( _fn.tpl[type] );
					}
				},
				remove: {
					element: function( e ) {
						var $btn = $(e.currentTarget),
							block = $btn.data('element'),
							sel = '.' + block,
							$el = $btn.closest(sel),
							$container = $el.parent();

						e.preventDefault();
						$el.detach();

						// If remove icon is hidden for last element of type
						if ( ( ( block === 'document' || block === 'milestone' ) &&  $container.children(sel).length === 1 ) ||
							 ( block === 'option-wrapper' && $container.children(sel).length === 2 ) ) {
							$container.children(sel).find('.remove-element').addClass('hidden');
						}
					}
				},
				reset: {
					dropdown: function( $el ) {
						$el.val('false');
					}
				},
				submit: function() {
				},
				update: {
					answer: function( e ) {
						var $el = $(e.currentTarget),
							$answers = $el.siblings('.answer-options'),
							type = $el.val();

						// Only show if multiple answers
						if ( type === 'radio' || type === 'checkbox' || type === 'select' ) {
							$answers.removeClass('hidden');
						} else {
							$answers.addClass('hidden');
						}
					}
				}
			},
			set: {
				dates: function( data ) {
					var dates = data.dates;

					_.each(_fn.data.projectcomponent, function(el) {
						var openObj = _.findWhere( dates, { name: el.open } ),
							closeObj = _.findWhere( dates, { name: el.close } );

						el.open = openObj ? openObj.date : '';
						el.close = closeObj ? closeObj.date : '';
					});
				}
			},
			submit: {
				tab: function( e ) {
					var $el = $(e.currentTarget),
						$form = $el.closest('form'),
						nextTab = $el.data('tab');

					e.preventDefault();

					if ( nextTab === 'overview' ) {
						_fn.build.submit.general( $form );
                    } else {
						_fn.build.submit.component( $form );
					}

					// go to next tab
					_fn.utils.tabs.load.params( nextTab );
					_fn.utils.tabs.current = nextTab;
				},
				general: function( $form ) {
					// get values from fields
					_fn.data.resources = _fn.build.form.get.documentData( $form.find('.resources') );
					_fn.data.submissions = _fn.build.form.get.documentData( $form.find('.submissions') );
					_fn.data.dates = _fn.build.form.get.milestoneData( $form.find('.dates') );

					_fn.build.datepicker.set();
				},
				component: function( $form ) {
					var data = _fn.build.form.get.componentData( $form ),
						component = $form.parent('.tab').data('tab');

					if ( ! $.isEmptyObject(data) ) {
						_fn.data.projectcomponent[component] = data;
					}
				},
				project: function( e ) {
					var $el = $(e.currentTarget),
						$form = $el.closest('form');

					e.preventDefault();
					_fn.build.submit.component( $form );
					_fn.build.set.dates( _fn.data );

					// Make AJAX call
					console.log('submit project ', _fn.data);
				}
			}
		},

		finish: function() {},

		utils: {
			datepicker: {
				init: function( $el ) {
					$el.pickadate({
						format: 'm/d/yyyy',
						min: new Date(),
						today: '',
						onClose: _fn.utils.datepicker.focusNext
					});
				},
				focusNext: function() {
					var $el = $(this.$node[0]),
						$milestone = $el.parent('.milestone'),
						$next = $milestone.next();

					if ( $next.hasClass('milestone') ) {
						$next = $next.children('.name');
					}

					$next.focus();
				}
			},
			tabs: {
				$el: {
				    header: $('.xblock--group-project .tab-headers li'),
					body: $('.xblock--group-project .tab')
				},
				init: function() {
					_fn.utils.tabs.clickHandlers();
				},
				clickHandlers: function() {
					var tabs = _fn.utils.tabs;

					tabs.$el.header.on( 'click', tabs.load.event );
				},
				current: 'general',
				load: {
					event: function( e ) {
						var $el = $(e.currentTarget),
							tab = $el.data('tab'),
							currentTab = _fn.utils.tabs.current,
							$form = _fn.utils.tabs.$el.body.find('.' + currentTab + '-form');

						e.preventDefault();

						_fn.utils.tabs.$el.header.removeClass('active');
						$el.addClass('active');
						_fn.utils.tabs.load.body( tab );

						// Submit the form
						if ( currentTab === 'general' ) {
							_fn.build.submit.general( $form );
						} else {
							_fn.build.submit.component( $form );
						}
						_fn.utils.tabs.current = tab;
					},
					params: function( tab ) {
						_fn.utils.tabs.$el.header.removeClass('active');
						_fn.utils.tabs.$el.header.filter('[data-tab=' + tab + ']' ).addClass('active');

						_fn.utils.tabs.load.body( tab );
					},
					body: function( tab ) {
						_fn.utils.tabs.$el.body.addClass('hidden');
						_fn.utils.tabs.$el.body.filter('[data-tab=' + tab + ']' ).removeClass('hidden');
					}
				}
			},
			// tinyMCE jQuery plugin
			texteditor: {
				init: function( $el ) {
					$el.tinymce({
						plugins: 'code link visualblocks',
						menubar: false,
					    toolbar: 'undo redo | bold italic underline | link bullist numlist code |  cut copy paste | styleselect',
					    statusbar: false,
					    style_formats:[
	                        {
	                            title: 'Headers',
	                            items: [
	                                { title: 'Header 1', format: 'h1' },
	                                { title: 'Header 2', format: 'h2' },
	                                { title: 'Header 3', format: 'h3' },
	                                { title: 'Header 4', format: 'h4' },
	                                { title: 'Header 5', format: 'h5' },
	                                { title: 'Header 6', format: 'h6' }
	                            ]
	                        }, {
	                            title: 'Inline',
	                            items: [
	                            	{ title: 'Bold', icon: 'bold', format: 'bold' },
	                            	{ title: 'Italic', icon: 'italic', format: 'italic' },
	                            	{ title: '_Underline', icon: 'underline', format: 'underline' },
	                            	{ title: 'Code', icon: 'code', format: 'code' }
	                            ]
	                        }, {
	                        	title: 'Blocks',
	                        	items: [
	                        		{ title: 'Paragraph', format: 'p' },
	                        		{ title: 'Blockquote', format: 'blockquote' },
	                        		{ title: 'Div', format: 'div' },
	                        		{ title: 'Pre', format: 'pre' }
	                    		]
	                    	}
				        ]
					});
				},
				getContent: function( $el ) {
					var content = $el.tinymce().getContent({
                        format: 'raw'
                    });

                    return _fn.utils.texteditor.cleanData( content );
				},
                cleanData: function( str ) {
                    // Change <br data-mce-bogus="1"> to <br>
                    return str.replace( /\sdata-mce-bogus="1"/g, '');
                }
			}
		},

		// group_project data
		data: {
			resources: [],
			submissions: [],
			dates: [],
			projectcomponent: {}
		}
	};

	return {
		builder: _fn.build.init
	};
})();

groupProject.builder();