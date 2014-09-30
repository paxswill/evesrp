var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.payouts = {

  markPaid: function markPaid(ev) {
    var $form = $(ev.target).closest('form');
    $.ajax( {
      type: 'POST',
      url: $form.attr('action'),
      data: $form.serialize(),
      success: EveSRP.ui.payouts.renderRequest
    });
    // Update entire list of requests (if within 10 second cooldown period)
    EveSRP.ui.payouts.getRequests();
    return false;
  },

  copyUpdate: function copyUpdate(client, args) {
    var $this = $(this),
        timeStamp = (new Date).getTime(),
        $panel = $this.closest('.panel');
    // Update this request, while adhering to the ratelimit
    if ((timeStamp - EveSRP.ui.payouts.lastRefresh) >
        EveSRP.ui.payouts.refreshDelay) {
      EveSRP.ui.payouts.updateRequest($panel.data('request-id'));
    }
  },

  renderRequest: function renderRequestPayout(request) {
    var $panelList = $('#requests'),
        $panel = $panelList.find('#request-' + request.id),
        $newPanel = $(Handlebars.templates.payout_panel(request)),
        $copyButtons;
    if ($panel.length !== 0) {
      // Remove old listeners and popover/tooltips
      $copyButtons = $panel.find('.copy-btn');
      $copyButtons.tooltip('destroy');
      EveSRP.ui.clipboardClient.unclip($copyButtons);
      $panel.find('.small-popover').popover('destroy');
      if ($panel.find('table.in').length !== 0) {
        $newPanel.find('table.collapse').addClass('in');
      }
      $panel.replaceWith($newPanel);
    } else {
      $panelList.append($newPanel);
    }
    // Attach events and activate tooltips/popovers
    $panel = $panelList.find('#request-' + request.id);
    $copyButtons = $panel.find('.copy-btn');
    EveSRP.ui.clipboardClient.clip($copyButtons);
    $copyButtons.tooltip({trigger: 'manual'});
    $panel.find('.small-popover').on('click', false).popover();
    $('.null-link').on('click', function(ev) {
      ev.preventDefault();
    });
  },

  getRequests: function getPayoutRequests() {
    var state = History.getState(),
        timeStamp = (new Date).getTime();
    // 7 second cooldown timer between list updates
    if ((timeStamp - EveSRP.ui.payouts.lastRefresh) <
          EveSRP.ui.payouts.refreshDelay) {
      return;
    } else {
      EveSRP.ui.payouts.lastRefresh = timeStamp;
      $.ajax( {
        type: 'GET',
        url: state.url,
        success: function(data) {
          _.each(data.requests, function(request) {
            EveSRP.ui.payouts.renderRequest(request);
          });
        }
      });
    }
  },

  updateRequest: function updatePayoutRequest(requestID) {
    $.ajax( {
      type: 'GET',
      url: $SCRIPT_ROOT + '/request/' + requestID,
      success: EveSRP.ui.payouts.renderRequest
    });
  },

  // Initialize to the parse time. This prevents trying to update the requests
  // immediately after loading the page (if refreshing a scrolled down page).
  lastRefresh: (new Date).getTime(),
  refreshDelay: 7000,

  infiniteScroll: function infiniteScroll(ev) {
    var $window = $(window),
        $document = $(document);
    if ($window.scrollTop() > ($document.height() - $window.height() - 300)) {
      EveSRP.ui.payouts.getRequests();
    }
  },

  setupEvents: function setupRequestListEvents() {
    var $window = $(window);
    EveSRP.ui.setupClipboard();
    EveSRP.ui.clipboardClient.on('complete', EveSRP.ui.payouts.copyUpdate);
    /* Initialize tooltips */
    $('.copy-btn').tooltip({trigger: 'manual'});
    EveSRP.ui.clipboardClient.on('mouseover', function (ev) {
      $(this).tooltip('show');
    }).on('mouseout', function(ev) {
      $(this).tooltip('hide');
    });
    // Initialize popovers
    $('.small-popover').on('click', false).popover();
    /* Add paid button events */
    $('#requests').on('submit', EveSRP.ui.payouts.markPaid);
    // Watch the history for state changes
    $window.on('statechange', this.getRequests);
    $window.on('scroll', EveSRP.ui.payouts.infiniteScroll);
    // Prevent default action for Action expansion links. Note, this doesn't
    // prevent bubbling of events, which is used by the collapse extension.
    $('.null-link').on('click', function(ev) {
      ev.preventDefault();
    });
  }
};
if ($('div#requests').length !== 0) {
  EveSRP.ui.payouts.setupEvents();
}
