function expand_title(page_num,num_on_page)
{
    var spans=document.getElementsByTagName("span");
    var i;
    for(i=0;i<spans.length;i++)
    {
        if(spans[i].getAttribute("num")==page_num+"_"+num_on_page)
        {
            spans[i].style.display="none";
            break;
        }
    }
    document.getElementById(page_num+"_"+num_on_page+"_full").style.display="inline";
}

function expand_buttons() {
    var page_buttons = $(".page_button");

    for (var i = 0; i < page_buttons.length; i++) {
        var pagenum = parseInt($(page_buttons[i]).text())

        var items = $("#page_" + pagenum + " ul li span.sort_by_field");
        var first_item = $(items[0]).text().trim().split(" ")[0].replace(",", "");
        var last_item_initial = $(items[items.length - 1]).text().trim();

        /*
        Options for this problem:
        Ignore no data items (A-Z)
        Include no data items (A-n.d.)
        Include both (A-Z and n.d.)
        */

        var n = 2;
        while(last_item_initial.lastIndexOf("not available") != -1) {
            last_item_initial = $(items[items.length - n]).text().trim();
            n++;
        }

        var last_item = last_item_initial.split(" ")[0].replace(",", "");

        $(page_buttons[i]).text(first_item + " — " + last_item);
    };
}

function hover_show(id) {
    $("#"+id+" div.extra").fadeTo(500, 1);
}

function hover_hide(id) {
    $("#"+id+" div.extra").fadeTo(500, 0);
}

function show_page(i)
{
    var old_page, new_page, buttons;
    old_page=document.getElementById("page_"+curr_page);
    old_page.style.display="none";
    
    new_page=document.getElementById("page_"+i);
    new_page.style.display="block";
    curr_page=i;
    
    buttons=document.getElementsByClassName("page_button");
    for(var j=0;j<buttons.length;j++) {
        buttons[j].style.background = "#F2D69E"
        buttons[j].style.borderColor = "#5e4f3e"
        buttons[j].style.color = "#5e4f3e"
    }
    buttons[parseInt(i)-1].style.background='#fff';
    buttons[parseInt(i)-1].style.borderColor='#8f2d1e';
    buttons[parseInt(i)-1].style.color='#8f2d1e';


    document.getElementById("prints_shown").innerHTML=((parseInt(i)-1)*prints_per_page+1)+"-"+(Math.min(parseInt(i)*prints_per_page, max_num));

    document.getElementById("curr_page_span").innerHTML=i;
}

function show_sorting(sorting)
{
    var links= $(".sort_options a.sort_link")
    if(links.length != 0) {
        for(var i=0;i<links.length;i++)
            links[i].style.fontWeight="normal";
        document.getElementById("sort_"+sorting).style.fontWeight="bold";
    }
}

function show_filter(filter)
{
    var links= $(".filter_options a.sort_link")
    if(links.length != 0) {
        for(var i=0;i<links.length;i++)
            links[i].style.fontWeight="normal";
        document.getElementById("sort_"+filter).style.fontWeight="bold";
    }
}

function show_collection(collection)
{
    var links=document.getElementsByClassName("sort_collection");
    for(var i=0;i<links.length;i++)
        links[i].style.fontWeight="normal";
    document.getElementById("collection_"+collection).style.fontWeight="bold";
}
