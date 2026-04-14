# PlayOnThere

Reproductor multimedia para Windows pensado para ejecutarse en un segundo monitor (o cualquier monitor). Permite cargar archivos y carpetas de video/audio, controlar volumen, elegir dispositivo de audio, poner en pantalla completa y guardar el estado de la sesion.

## Tabla de contenidos

- [Descargar e instalar](#descargar-e-instalar)
  - [Opción 1: Instalador (recomendado)](#opción-1-instalador-recomendado)
  - [Opción 2: Portable (sin instalacion)](#opción-2-portable-sin-instalacion)
- [Primer uso](#primer-uso)
- [Ejecutar desde codigo fuente](#ejecutar-desde-codigo-fuente)
  - [Requisitos](#requisitos)
  - [Clonar y ejecutar](#clonar-y-ejecutar)
- [Compilar ejecutable](#compilar-ejecutable)
- [Configuracion](#configuracion)
- [Dependencias](#dependencias)
- [Reportar problemas](#reportar-problemas)
- [Licencia](#licencia)

---

## Descargar e instalar

Ve a la pagina de releases para obtener la ultima version:

**https://github.com/YoeKimera/PlayOnThere/releases/latest**

Encontraras dos opciones de descarga:

| Archivo | Descripcion |
|---|---|
| `PlayOnThere-Setup.exe` | Instalador para Windows. Instala la app y crea accesos directos. |
| `PlayOnThere-portable.zip` | Version portable. No requiere instalacion, solo descomprimir y ejecutar. |

---

### Opción 1: Instalador (recomendado)

1. Descarga `PlayOnThere-Setup.exe` desde [releases](https://github.com/YoeKimera/PlayOnThere/releases/latest).
2. Ejecuta el instalador.
3. Si Windows SmartScreen lo bloquea, haz clic en **"Mas informacion"** → **"Ejecutar de todas formas"**.
4. Sigue el asistente de instalacion.
5. Abre PlayOnThere desde el menu Inicio o el acceso directo del escritorio.

Para desinstalar, usa "Agregar o quitar programas" en la configuracion de Windows.

---

### Opción 2: Portable (sin instalacion)

1. Descarga `PlayOnThere-portable.zip` desde [releases](https://github.com/YoeKimera/PlayOnThere/releases/latest).
2. Descomprime el archivo en la carpeta que prefieras (por ejemplo `C:\Tools\PlayOnThere`).
3. Entra a la carpeta descomprimida y ejecuta `PlayOnThere.exe`.
4. Si Windows SmartScreen aparece, selecciona **"Mas informacion"** → **"Ejecutar de todas formas"**.

> La version portable guarda la configuracion (`playonthere_config.json`) en la misma carpeta donde esta el ejecutable, por lo que puedes llevarla en un pendrive o moverla libremente.

---

## Primer uso

1. Abre la aplicacion.
2. Usa **"Agregar archivos"** o **"Agregar carpeta"** para cargar tu contenido multimedia.
3. En la seccion de **Monitor**, elige el monitor donde quieres reproducir el video (util para segundo monitor o TV).
4. En la seccion de **Audio**, elige el dispositivo de salida de audio que prefieras.
5. Ajusta el volumen con el control deslizante.
6. Presiona **Play** para comenzar la reproduccion.
7. Usa el boton de **pantalla completa** para expandir el video en el monitor seleccionado.
8. El estado de la sesion se guarda automaticamente en `playonthere_config.json` para que al volver a abrir la app retomes donde dejaste.

---

## Ejecutar desde codigo fuente

### Requisitos

- Windows 10 o Windows 11
- Python 3.11 o superior
- [VLC media player](https://www.videolan.org/vlc/) instalado en `C:\Program Files\VideoLAN\VLC` (requerido por `python-vlc`)
- Git

### Clonar y ejecutar

```powershell
# 1. Clonar el repositorio
git clone https://github.com/YoeKimera/PlayOnThere.git
cd PlayOnThere

# 2. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicacion
python main.py
```

---

## Compilar ejecutable

El proyecto incluye scripts de PowerShell para generar el ejecutable y el instalador.

```powershell
# Genera el ejecutable en dist/
.\build_dist.ps1

# Genera el instalador en installer/
.\build_installer.ps1
```

Requisitos adicionales para compilar:
- [PyInstaller](https://pyinstaller.org/) (incluido en `requirements.txt`)
- [Inno Setup](https://jrsoftware.org/isinfo.php) instalado (para `build_installer.ps1`)

Los archivos de salida seran:
- `dist\PlayOnThere-portable.zip` — version portable lista para distribuir
- `installer\PlayOnThere-Setup.exe` — instalador de Windows

---

## Configuracion

La app guarda su estado y preferencias en `playonthere_config.json`, que se crea automaticamente en la misma ubicacion que el ejecutable (o en la raiz del proyecto si se ejecuta desde codigo fuente).

El archivo almacena informacion como:
- Monitor seleccionado
- Dispositivo de audio seleccionado
- Volumen
- Lista de archivos cargados
- Posicion de reproduccion

---

## Dependencias

| Paquete | Uso |
|---|---|
| `PySide6` | Interfaz grafica (Qt 6) |
| `python-vlc` | Reproduccion multimedia via VLC |
| `screeninfo` | Deteccion de monitores conectados |

---

## Reportar problemas

Si encuentras un bug o quieres pedir una mejora:

**https://github.com/YoeKimera/PlayOnThere/issues**

Incluye en tu reporte: version de Windows, version de PlayOnThere y descripcion del problema.

---

## Licencia

Si vas a distribuir o reutilizar este proyecto, agrega aqui la licencia oficial del repositorio.
