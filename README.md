# PlayOnThere

**Reproductor de multimedia con selección de pantalla y dispositivo de sonido.**

PlayOnThere te permite reproducir archivos multimedia utilizando el motor de VLC,
eligiendo en qué pantalla se muestra el vídeo y qué dispositivo de audio se utiliza.
Ideal para escenarios, proyectores o pantallas secundarias.

---

## Características

- 🎬 Motor de reproducción VLC (`python-vlc` / libvlc).
- 🖥️ Selección de la pantalla de reproducción (admite múltiples monitores).
- 🔊 Selección del dispositivo de audio de salida.
- ⏯️ Controles de reproducción: reproducir, pausar/reanudar y detener.
- 🔊 Control de volumen (0–200 %).
- ⏩ Barra de progreso con búsqueda por arrastre.
- ⛶ Alternancia de pantalla completa en la ventana de vídeo.
- Soporta vídeo (MP4, MKV, AVI, MOV, WMV…) y audio (MP3, FLAC, OGG…).

---

## Requisitos

- Python 3.10 o superior.
- [VLC media player](https://www.videolan.org/vlc/) instalado en el sistema
  (libvlc debe estar disponible en el `PATH`).
- Las dependencias de Python listadas en `requirements.txt`.

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/YoeKimera/PlayOnThere.git
cd PlayOnThere

# Instalar dependencias de Python
pip install -r requirements.txt
```

> **Linux:** asegúrate de tener instalado también `python3-tk` (p. ej.
> `sudo apt install python3-tk vlc`).

---

## Uso

```bash
python playonthere.py
```

1. Haz clic en **Examinar…** y selecciona tu archivo multimedia.
2. Elige la **Pantalla de reproducción** en la lista desplegable.
3. Elige el **Dispositivo de sonido** deseado.
4. Ajusta el volumen con el deslizador.
5. Pulsa **▶ Reproducir**. El vídeo se abrirá en la pantalla seleccionada.
6. Usa **⏸ Pausar / ▶ Reanudar**, **⏹ Detener** y **⛶ Pantalla completa** según necesites.

---

## Pruebas

```bash
python -m pytest tests/ -v
```

---

## Licencia

MIT
