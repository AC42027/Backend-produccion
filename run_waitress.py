from waitress import serve
from mi_formulario.wsgi import application

serve(application, host='0.0.0.0', port=8080)
