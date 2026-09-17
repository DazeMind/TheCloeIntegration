import json
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from google import genai

# ============================================
# Cliente de Gemini
# ============================================
client = genai.Client(api_key=settings.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Eres un asistente experto en el SII de Chile y en boletas de honorarios. "
    "Respondes de forma clara, breve y en español neutro. "
    "Si no sabes algo, lo dices honestamente y sugieres consultar sii.cl."
)

chat_sessions = {}


def get_session(session_id, reset=False):
    if reset and session_id in chat_sessions:
        del chat_sessions[session_id]

    if session_id not in chat_sessions:
        chat_sessions[session_id] = client.chats.create(
            model=settings.GEMINI_MODEL,
            config={"system_instruction": SYSTEM_INSTRUCTION},
        )

    return chat_sessions[session_id]


def index(request):
    return render(request, 'chatbot/index.html')


def widget(request):
    session_id = request.COOKIES.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())

    response = render(request, 'chatbot/widget.html', {'session_id': session_id})
    response.set_cookie('chat_session_id', session_id, max_age=60 * 60 * 24 * 7)
    return response


@csrf_exempt
@require_POST
def chat_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    user_message = (data.get('message') or '').strip()
    session_id = data.get('session_id') or request.COOKIES.get('chat_session_id', 'default')

    if not user_message:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    if not settings.GEMINI_API_KEY:
        return JsonResponse({'error': 'Falta GEMINI_API_KEY en .env'}, status=500)

    try:
        chat = get_session(session_id)
        response = chat.send_message(user_message)
        return JsonResponse({'reply': response.text, 'session_id': session_id})
    except Exception as e:
        return JsonResponse({'error': f'Error con Gemini: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST', 'DELETE'])
def reset_chat(request):
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    session_id = data.get('session_id') or request.COOKIES.get('chat_session_id', 'default')
    get_session(session_id, reset=True)
    return JsonResponse({'ok': True, 'session_id': session_id})