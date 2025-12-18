from django.shortcuts import render
import json
import ollama
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
@csrf_exempt
def chat_view(request):
    if request.method=='POST':
        try:
            # 1. Get the message from the user
            data=json.loads(request.body)
            user_message=data.get('message','')

            # 2 Ask ollama
            response=ollama.chat(model='qwen3:8b',messages=[
                {
                    'role':'user',
                    'content':user_message,
                    },
            ])

            # 3 send the answer back
            bot_reply=response['message']['content']
            return JsonResponse({'reply':bot_reply})
        except Exception as e:
            return JsonResponse({'reply':f"Error: {str(e)}"})
    return JsonResponse({'error':'Invalid request'},status=400)    