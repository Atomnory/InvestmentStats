import os
import matplotlib.pyplot as plt
from django.shortcuts import render

from config.settings import MEDIA_ROOT
from .models import Securities, PieGraph
from django.db.models.fields.files import ImageFieldFile, FileField


def index_page(request):

    if request.method == 'POST':
        graph_name = get_updated_graph()
        try:
            PieGraph.objects.get(pk=1)
            print('$$ PieGraph exists')
        except PieGraph.DoesNotExist:
            graph = PieGraph(pk=1, graph=ImageFieldFile(instance=None, name=graph_name, field=FileField()))
            print('$$ create new PieGraph')
            graph.save()

    try:
        graph = PieGraph.objects.get(pk=1).graph
    except PieGraph.DoesNotExist:
        graph = None

    securities_list = Securities.objects.all()

    index_page_data = {
        'securities': securities_list,
        'graph': graph
    }

    return render(request, 'investments/index.html', index_page_data)


def get_updated_graph():
    securities_list = Securities.objects.all()
    data = [x.price * x.quantity for x in securities_list]
    labels = [x.ticker for x in securities_list]
    print('$$ update graph')
    graph_name = os.path.join('pie_graph', 'securities_pie.png')
    graph_path = os.path.join(MEDIA_ROOT, graph_name)
    plt.switch_backend('AGG')
    plt.pie(data, labels=labels, autopct='%1.1f%%')
    # fig, ax = plt.subplots()
    # ax.pie()
    plt.savefig(graph_path)
    # plt.show()
    return graph_name


