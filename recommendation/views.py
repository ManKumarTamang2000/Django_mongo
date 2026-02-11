from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from .vector_search import search_similar_animals
import json


def recommend_animals(request):
    if request.method == "POST":
        body = json.loads(request.body)
        query = body.get("query", "")

        results = search_similar_animals(query)

        return JsonResponse({"results": results})

    return JsonResponse({"error": "POST request required"})

