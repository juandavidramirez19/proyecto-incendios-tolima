# Guía paso a paso: Visual Studio Code y GitHub en Windows

## 0. Programas que debes instalar (una sola vez)
1. **Python 3.10 o superior**: https://www.python.org/downloads/ . En el instalador marca **"Add python.exe to PATH"**.
2. **Visual Studio Code**: https://code.visualstudio.com/
3. **Git**: https://git-scm.com/download/win (todas las opciones por defecto).
4. Cuenta gratuita en https://github.com
Comprueba abriendo **PowerShell** (tecla Windows, escribe "PowerShell"):
```powershell
python --version
git --version
```

## 1. Descargar y organizar los archivos
1. Descarga `proyecto-incendios-tolima.zip` desde el chat.
2. Clic derecho → **Extraer todo** y elige, por ejemplo, la carpeta Documentos.
3. Debe quedar una carpeta `proyecto-incendios-tolima` con `src`, `data`, `docs`, `tests`, `README.md`, etc.
   (que no quede una carpeta dentro de otra con el mismo nombre).

## 2. Abrir en Visual Studio Code
1. Abre VS Code → **File → Open Folder…** → elige `proyecto-incendios-tolima`.
2. Si pregunta si confías en los autores, elige **Yes, I trust**.
3. Instala la extensión **Python** (icono de cuadritos de la izquierda, busca "Python", de Microsoft).
4. Abre la terminal integrada: menú **Terminal → New Terminal**. Debe mostrar la ruta de tu proyecto.

## 3. Crear y activar el entorno virtual (en esa terminal)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```
Debe aparecer `(.venv)` al inicio de la línea. Si da un error de "scripts deshabilitados", ejecuta una vez:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
y repite la activación. Si VS Code pregunta por el nuevo entorno, elige **Yes**. Si no: `Ctrl+Shift+P` →
**Python: Select Interpreter** → el que dice `.venv`.

## 4. Instalar dependencias
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Ejecutar pruebas y pipeline
```powershell
python -m pytest -q
python -m src.pipeline
```
El pipeline necesita internet para consultar la API del IDEAM. Sin internet: `python -m src.pipeline --meteo ninguna`.
Mientras corre verás los pasos en la consola; el mismo texto queda en `outputs\log_ejecucion.txt`.

## 6. Comprobar que se generaron los archivos
```powershell
dir data\processed
dir outputs
Get-Content outputs\reporte_validaciones.csv
Get-Content outputs\reporte_cobertura_meteo.csv
```
Revisa que `data\processed\alertas_tolima_final.csv` exista, que `reporte_validaciones.csv` no tenga `FALLA` y
mira en `reporte_cobertura_meteo.csv` el `estado` de cada variable (`OK`, `SIN_DATOS_EN_PERIODO`, `ERROR_RED`...).
Las figuras están en `outputs\figuras`.

## 7. Capturas de pantalla (evidencia)
Crea la carpeta `outputs\evidencias` y guarda ahí capturas (tecla Windows + Shift + S) de: la terminal con las
pruebas pasadas, la terminal con el pipeline terminado, el contenido de `outputs`, y el historial de Git.

## 8. Subir a GitHub
**8.1 Configurar Git (una sola vez)**
```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo@ejemplo.com"
```
**8.2 Crear el repositorio local y los primeros commits** (cada commit guarda un avance)
```powershell
git init
git add src tests requirements.txt .gitignore
git commit -m "Agrega pipeline en src y pruebas automaticas"
git add notebooks data/raw
git commit -m "Agrega notebook original y datos originales"
git add README.md docs
git commit -m "Agrega README, informe tecnico y registro de pruebas"
```
**8.3 Crear el repositorio en GitHub**
1. Entra a github.com → botón **New** (o **+ → New repository**).
2. Nombre: `proyecto-incendios-tolima`. Déjalo **sin** README, sin .gitignore y sin licencia. **Create repository**.
3. Copia la dirección que termina en `.git` (por ejemplo `https://github.com/TU_USUARIO/proyecto-incendios-tolima.git`).

**8.4 Conectar y subir**
```powershell
git branch -M main
git remote add origin https://github.com/TU_USUARIO/proyecto-incendios-tolima.git
git push -u origin main
```
La primera vez se abre una ventana del navegador para iniciar sesión en GitHub. Después recarga la página del repositorio.

## 9. Guardar avances después (commits)
Después de ejecutar el pipeline (para subir también los resultados):
```powershell
git status
git add data/processed outputs
git commit -m "Agrega resultados de la ejecucion del pipeline"
git push
```
Para cualquier cambio posterior:
```powershell
git add .
git commit -m "Describe aqui lo que cambiaste"
git push
```
Ver el historial (evidencia de commits): `git log --oneline`

## Problemas frecuentes
| Síntoma | Solución |
|---|---|
| `python` no se reconoce | Reinstala Python marcando "Add python.exe to PATH" y abre una terminal nueva |
| `No module named src` | Ejecuta desde la carpeta del proyecto y usa `python -m src.pipeline` (con `-m`) |
| `No module named pandas` | El entorno no está activo (falta `(.venv)`) o no corriste `pip install -r requirements.txt` |
| `ERROR_RED` en la cobertura | Sin internet o acceso bloqueado a datos.gov.co; reintenta con otra red |
| `git push` rechazado | Verifica que el repositorio de GitHub esté vacío y que la dirección de `origin` sea correcta |
