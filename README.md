# PlayOnThere

Reproductor multimedia para Windows pensado para ejecutarse en un segundo monitor.

## Enlaces

- Repositorio: https://github.com/YoeKimera/PlayOnThere
- Releases: https://github.com/YoeKimera/PlayOnThere/releases
- Ultimo release: https://github.com/YoeKimera/PlayOnThere/releases/latest
- Reportar bugs o pedir mejoras: https://github.com/YoeKimera/PlayOnThere/issues

## Que incluye el release

En cada version publicada normalmente encontraras:

- `PlayOnThere-Setup.exe`: instalador para Windows.
- `PlayOnThere-portable.zip`: version portable sin instalacion.

## Tutorial 1: Instalacion rapida (Setup)

1. Entra a la pagina de releases: https://github.com/YoeKimera/PlayOnThere/releases/latest
2. Descarga `PlayOnThere-Setup.exe`.
3. Ejecuta el instalador y completa el asistente.
4. Abre PlayOnThere desde el menu Inicio o acceso directo.

## Tutorial 2: Uso en modo portable

1. Descarga `PlayOnThere-portable.zip` desde: https://github.com/YoeKimera/PlayOnThere/releases/latest
2. Descomprime el archivo en la carpeta que prefieras.
3. Ejecuta `PlayOnThere.exe`.
4. Si Windows SmartScreen aparece, selecciona "Mas informacion" y luego "Ejecutar de todas formas" si confias en el origen.

## Tutorial 3: Primer uso (paso a paso)

1. Abre la aplicacion.
2. Carga tus archivos multimedia o una carpeta.
3. Elige el monitor secundario en la configuracion de pantalla/monitor.
4. Ajusta volumen, pantalla completa y dispositivo de audio segun necesidad.
5. Guarda configuracion para retomar sesion mas rapido.

## Ejecutar desde codigo fuente

### Requisitos

- Windows 10/11
- Python 3.11+

### Pasos

1. Clona el repositorio.
2. Crea y activa un entorno virtual.
3. Instala dependencias con `requirements.txt`.
4. Ejecuta la app con `python main.py`.

Ejemplo en PowerShell:

```powershell
git clone https://github.com/YoeKimera/PlayOnThere.git
cd PlayOnThere
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Compilar ejecutable

El proyecto incluye scripts para generar distribucion e instalador:

- `build_dist.ps1`
- `build_installer.ps1`

Ejecuta en PowerShell desde la raiz del proyecto:

```powershell
.\build_dist.ps1
.\build_installer.ps1
```

## Configuracion

La app guarda estado y preferencias en `playonthere_config.json`.

## Licencia

Si vas a distribuir o reutilizar este proyecto, agrega aqui la licencia oficial del repositorio.
