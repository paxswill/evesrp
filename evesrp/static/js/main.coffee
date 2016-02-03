# jQuery needs to be global for Bootstrap plugins to work properly
unless global.jQuery?
    global.jQuery = require 'jquery'
require 'bootstrap/js/dropdown'
require 'bootstrap/js/tab'
require 'bootstrap/js/transition'
require 'bootstrap/js/collapse'

Handlebars = require 'hbsfy/runtime'
registerHelpers = (require 'evesrp/handlebars-helpers').registerHelpers
registerHelpers Handlebars

ui = require 'evesrp/common-ui'
division = require 'evesrp/division'
request = require 'evesrp/request'
filter = require 'evesrp/filter'
requestList = require 'evesrp/requestList'
payouts = require 'evesrp/payouts'

unless (jQuery '#mocha').length != 0
    ui.setupEvents()
    i18nPromise = ui.setupTranslations()
    if (jQuery '.entity-typeahead').length != 0
        division.setupEvents()
    if (jQuery '#actionMenu').length != 0
        request.setupEvents()
    if (jQuery '.filter-tokenfield').length != 0
        i18nPromise.done () ->
            filter.createFilterBar '.filter-tokenfield'
    if (jQuery 'table#requests').length != 0
        requestList.setupEvents()
    if (jQuery 'div#requests').length != 0
        payouts.setupEvents()
