# jQuery needs to be global for Bootstrap plugins to work properly
unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/dropdown'
require 'bootstrap/js/tab'
require 'bootstrap/js/transition'
require 'bootstrap/js/collapse'

Handlebars = require 'hbsfy/runtime'
registerHelpers = (require './handlebars-helpers').registerHelpers
registerHelpers Handlebars

ui = require './ui/common'
division = require './ui/division'
request = require './ui/request'

ui.setupEvents()
if (jQuery '.entity-typeahead').length != 0
    division.setupEvents()
if (jQuery '#actionMenu').length != 0
    request.setupEvents()
