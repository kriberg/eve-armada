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
    return parseFloat(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/*
 *  Page inits
 */
var init_eve_items = function () {
    $(".collapse").collapse({toggle:false});
    $.getJSON('/eve/typeahead/invtype_name/', function(data) {
        $('#item-name-search').typeahead({source: data});
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

var delayed_load = function (field, url, taskid) {
    var id = '#' + field;
    $.get(url, function(data) {
        $(id).replaceWith(data);
        $(id).hide();
        $(id).fadeIn('slow');
    });
}


