@echo off
echo ========================================
echo   Disney Trip - Rastreador de Gastos
echo ========================================
echo.

if exist "venv\Scripts\activate" (
    echo Ativando ambiente virtual...
    call venv\Scripts\activate
) else (
    echo Nenhum venv encontrado, usando Python global...
)

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Iniciando servidor em http://localhost:5000
echo.
python app.py

pause
