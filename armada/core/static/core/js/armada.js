/*
 * jQuery django integration
 */
$.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                // Only send the token to relative URLs i.e. locally.
                xhr.setRequestHeader("X-CSRFToken",
                                     $("#csrfmiddlewaretoken").val());
            }
        }
    });
jQuery(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

/*
 * Helper functions
 */
var printisk = function (v) {
    return $.format.number(parseFloat(v), '#,##0.00#');
}

/*
 *  Page inits
 */
var init_eve_items = function () {
    $(".collapse").collapse({toggle:false});
    $.getJSON('/eve/typeahead/invtype_name/', function(data) {
        $('#item-name-search').typeahead({source: data, items: 30});
    });
}

var init_location_typeahead = function (selector) {
    $(".collapse").collapse({toggle:false});
    $.getJSON('/eve/typeahead/location_name/', function(data) {
        $(selector).typeahead({source: data, items: 30});
    });
}

var init_invtype_typeahead = function (selector) {
    $(".collapse").collapse({toggle:false});
    $.getJSON('/eve/typeahead/invtype_name/', function(data) {
        $(selector).typeahead({source: data, items: 30});
    });
}

var init_price_columns = function () {
    var ismap = {};
    $("span.system-item-price").each(function (i, v) {
        var parts = $(v).attr('name').split(':');
        var system = '' + parts[0];
        var item = '' + parts[1];
        if(!ismap[system])
            ismap[system] = [];
        ismap[system].push(item);
    });
    for(var system in ismap) {
        (function(system) {
        $.post('/core/data/prices/'+system+'/',
               {items: ismap[system]},
               function(data) {
                   for(var item in data) {
                       var fields = $('span.system-item-price[name="'+system+':'+item+'"]');
                       fields.text('');
                       fields.append('<span class="price-buy">'+printisk(data[item][0])+'</span><br /><span class="price-sell">'+printisk(data[item][1])+'</span>');
                       fields.closest('td').addClass('number');
                   }
                },
              'json');
        })(system);
    }
}

var init_isk_span = function () {
    $("span.isk").each(function (i, v) {
        v.textContent = printisk(v.textContent) + ' ISK';
    });
}

var delayed_load = function (taskid, url) {
    var id = '#' + taskid;
    $.get(url, function(data) {
        $(id).replaceWith(data);
        $(id).hide();
        $(id).fadeIn('slow');
    });
}

var tq_countdown = function (timestamp, id) {
    var target_time = new Date(timestamp*1000);
    var component = function (x, v) {
        return Math.floor(x / v);
    }
    var element = $('#'+id);
    var counter = function() {
        current = new Date();
        diff = (target_time-current)/1000;
        var days    = component(diff, 24 * 60 * 60),
            hours   = component(diff,      60 * 60) % 24,
            minutes = component(diff,           60) % 60,
            seconds = component(diff,            1) % 60;
        var txt = '';
        if(days > 0)
            txt += days+'d ';
        if(hours > 0)
            txt += hours+'h ';
        if(minutes > 0)
            txt += minutes+'min ';
        if(seconds > 0)
            txt += seconds+'s';
        element.text(''+days+'d '+hours+'h '+minutes+'min '+seconds+'s');
        setTimeout(counter, 1000);
    }
    counter();
    setTimeout(counter, 1000);
}
