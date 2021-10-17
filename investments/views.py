from django.shortcuts import render

from .services import get_index_forms, get_graph_if_exist_or_create, get_formatted_securities_list


def index_page(request):
    forms = get_index_forms(request)
    graph = get_graph_if_exist_or_create()
    securities = get_formatted_securities_list()

    index_page_data = {
        'securities': securities,
        'graph': graph,
        'form_creating': forms['form_creating'],
        'form_deleting': forms['form_deleting'],
        'form_increasing': forms['form_increasing']
    }

    return render(request, 'investments/index.html', index_page_data)
