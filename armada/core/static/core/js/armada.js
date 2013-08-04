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
        element.text(txt);
        setTimeout(counter, 1000);
    }
    counter();
    setTimeout(counter, 1000);
}

var init_asset_tree = function(json_url, element) {
    console.log(json_url);
    $.ui.fancytree.debugLevel = 1;
    $(function() {
        $(element).fancytree({
            extensions: ["filter", "table"],
            table: {
                indentation: 20,
                nodeColumnIdx: null
            },
            source: {
                url: json_url
            },
            lazyload: function(e, data) {
                data.result = $.ajax({
                    url: json_url+'?node='+data.node.key,
                    dataType: "json"
                });
            },
            click: function(e, data) {
                data.node.toggleExpanded();
            },
            rendercolumns: function(e, data) {
                var node = data.node;
                var span = node.span;
                var item = node.data;
                var $tdList = $(node.tr).find(">td");
                var padding = 'margin-left: '+ 20*(node.getLevel()-1) +'px;'
                var itemtitle = '<span class="fancytree-expander" style="'+padding+'"></span>';
                itemtitle += '<img src="http://image.eveonline.com/Type/' + item.typeid + '_32.png" alt="">';
                itemtitle += '<span class="fancytree-title" >'+ node.title + '</span>';
                $tdList.eq(0).html(itemtitle);
                $tdList.eq(1).text(item.q);
            },
            filter: {
            }
        });
        var tree = $(element).fancytree("getTree");

        $("input[name=search]").keyup(function(e) {
            var match = $(this).val();
            if(e && e.which === $.ui.keyCode.ESCAPE || $.trim(match) === ""){
                $("button#reset").click();
                return;
            }
            tree.options.filter.mode = $("input#hide").is(":checked") ? "hide" : "dimm";
            var num_matches = tree.applyFilter(match);
            $("button#reset").attr("disabled", false);
            $("span#matches").text(num_matches + ' stack(s) found');
        }).focus();

        $("button#reset").click(function(e) {
            $("input[name=search]").val("");
            $("span#matches").text("");
            tree.clearFilter();
        }).attr("disabled", true);
        
        $("button#collapse").click(function(e) {
            $(element).fancytree("getRootNode").visit(function(node) {
                node.setExpanded(false);
            });
        });

        $("button#expand").click(function(e) {
            $(element).fancytree("getRootNode").visit(function(node) {
                node.setExpanded(true);
            });
        });
        $("input#hide").change(function(e){
            tree.options.filter.mode = $(this).is(":checked") ? "hide" : "dimm";
            tree.clearFilter();
            $("input[name=search]").keyup();
        });


    });
}
