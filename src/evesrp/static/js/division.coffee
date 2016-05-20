jQuery = require 'jquery'
require 'selectize'
capitalize = require 'underscore.string/capitalize'
ui = require 'evesrp/common-ui'
entityTableTemplate = require 'evesrp/templates/entity_table'
entityOptionTemplate = require 'evesrp/templates/entity_option'


render = (entities) ->
    translationPromise = ui.setupTranslations()
    for permission in ['submit', 'review', 'pay', 'audit', 'admin']
        $table = (jQuery "##{ permission }").find 'table'
        translationPromise.done () ->
            newTable = entityTableTemplate {
                entities: entities[permission]
                # This is not localized, as it's a programmatic identifier
                # used in a form.
                name: permission
            }
            $table.replaceWith newTable


selectAttribute = () ->
    $this = jQuery this
    attr = ($this.find 'option:selected').val()
    unless attr == ''
        ($this.find 'options[values=""]').remove()
    jQuery.ajax {
        type: 'GET'
        url: "#{ window.location.pathname }transformers/#{ attr }/"
        success: (data) ->
            $transformerSelect = jQuery 'select#transformer'
            $transformerSelect.empty()
            choices = data[attr]
            $transformerSelect.prop 'disabled', (choices.length == 1)
            for choice in choices
                $option = jQuery '<option></option>'
                $option.append choice[1]
                $option.attr 'value', choice[0]
                if choice[2] == true
                    $option.prop 'selected', true
                $transformerSelect.append $option
    }
    true


selectTransformer = () ->
    $this = jQuery this
    $form = $this.parents 'form'
    jQuery.ajax {
        type: 'POST'
        url: window.location.pathname
        data: $form.serialize()
    }
    true


createEntitySelect = (selector) ->
    $selects = jQuery selector
    ui.setupTranslations().done () ->
        $selects.selectize {
            options: []
            openOnFocus: false
            closeAfterSelect: true
            dropdownParent: 'body'
            searchField: ['name']
            valueField: 'id'
            labelField: 'name'
            optgroups: {value: type} for type in ['User', 'Group']
            optgroupValueField: 'value'
            optgroupLabelField: 'value'
            optgroupField: 'type'
            onChange: (entityID) ->
                selectize = this
                $form = selectize.$input.closest 'form'
                $id = $form.find '#id_'
                $id.val entityID
                jQuery.ajax {
                    type: 'POST'
                    data: $form.serialize()
                    success: (data) ->
                        # Clear selection control now that this entity has been
                        # added
                        selectize.clear(true)
                        $id.val ''
                    complete: (jqxhr) ->
                        data = jqxhr.responseJSON
                        render data.permissions
                }
            render: {
                option: (item, escape) ->
                    entityOptionTemplate item
                optgroup_header: (data, escape) ->
                    # data will be either 'user' or 'group' as specified in the
                    # various optgroup related options above.
                    i18n_value = ui.i18n.gettext (capitalize data.value)
                    "<div class=\"optgroup-header\"> #{ escape(i18n_value) }s</div>"
            }
        }

    addEntityOptions = (data) ->
        if 'users' of data
            entities = data.users
        else if 'groups' of data
            entities = data.groups
        $selects.each () ->
            @selectize.addOption entities

    usersRequest = jQuery.ajax {
        type: 'GET'
        url: "#{ scriptRoot }/user/"
        success: addEntityOptions
    }
    groupsRequest = jQuery.ajax {
        type: 'GET'
        url: "#{ scriptRoot }/group/"
        success: addEntityOptions
    }


setupEvents = () ->
    (jQuery 'select#attribute').change selectAttribute
    (jQuery 'select#transformer').change selectTransformer
    createEntitySelect '.entity-typeahead'
    (jQuery '.permission').submit (ev) ->
        $form = (jQuery ev.target)
        jQuery.ajax {
            type: 'POST'
            url: window.location.pathname
            data: $form.serialize()
            complete: (jqxhr) ->
                data = jqxhr.responseJSON
                render data.permissions
        }
        false

exports.setupEvents = setupEvents
