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

ui = require './common-ui'
division = require './division'
request = require './request'
filter = require './filter'
requestList = require './requestList'
payouts = require './payouts'

ui.setupEvents()
ui.setupTranslations()
if (jQuery '.entity-typeahead').length != 0
    division.setupEvents()
if (jQuery '#actionMenu').length != 0
    request.setupEvents()
if (jQuery '.filter-tokenfield').length != 0
    filter.createFilterBar '.filter-tokenfield'
if (jQuery 'table#requests').length != 0
    requestList.setupEvents()
if (jQuery 'div#requests').length != 0
    payouts.setupEvents()
