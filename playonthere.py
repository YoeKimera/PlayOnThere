#!/usr/bin/env python3
"""
PlayOnThere - Reproductor de multimedia con selección de pantalla y dispositivo de sonido.

Utiliza el motor de VLC para reproducir contenido multimedia en una pantalla específica
con un dispositivo de audio seleccionado. Ideal para escenarios, proyectores o pantallas
secundarias.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import vlc
except ImportError:
    print("Error: python-vlc no está instalado. Ejecuta: pip install python-vlc")
    sys.exit(1)

try:
    from screeninfo import get_monitors
except ImportError:
    print("Error: screeninfo no está instalado. Ejecuta: pip install screeninfo")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Video window
# ---------------------------------------------------------------------------

class VideoWindow:
    """Ventana de reproducción de vídeo posicionada en una pantalla específica."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.root = tk.Toplevel()
        self.root.title("PlayOnThere")
        self.root.configure(bg="black")
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self._fullscreen = False

        self.frame = tk.Frame(self.root, bg="black")
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.root.update()

    # ------------------------------------------------------------------
    def get_window_id(self) -> int:
        """Devuelve el identificador nativo de la ventana para que VLC pueda incrustarse."""
        return self.frame.winfo_id()

    def toggle_fullscreen(self) -> None:
        """Alterna entre pantalla completa y modo ventana."""
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def is_alive(self) -> bool:
        """Comprueba si la ventana todavía existe."""
        try:
            return bool(self.root.winfo_exists())
        except tk.TclError:
            return False

    def destroy(self) -> None:
        """Destruye la ventana si todavía existe."""
        if self.is_alive():
            self.root.destroy()


# ---------------------------------------------------------------------------
# Helper utilities (testable without a display)
# ---------------------------------------------------------------------------

def format_time(ms: int) -> str:
    """Formatea milisegundos como M:SS (por ejemplo, 3:07)."""
    if ms < 0:
        return "0:00"
    total_s = ms // 1000
    m, s = divmod(total_s, 60)
    return f"{m}:{s:02d}"


def build_screen_list(monitors) -> list:
    """Convierte objetos Monitor en diccionarios con los datos necesarios."""
    screens = []
    for i, m in enumerate(monitors):
        name = getattr(m, "name", None) or f"Pantalla {i + 1}"
        screens.append(
            {
                "label": f"{name} ({m.width}×{m.height})",
                "x": m.x,
                "y": m.y,
                "width": m.width,
                "height": m.height,
            }
        )
    return screens


def enumerate_audio_outputs(vlc_instance) -> list:
    """
    Enumera los dispositivos de salida de audio disponibles a través de libvlc.

    Devuelve siempre al menos la entrada "Predeterminado".
    """
    outputs = [{"label": "Predeterminado", "module": None, "device": None}]
    try:
        ao_list = vlc_instance.audio_output_list_get()
        if not ao_list:
            return outputs
        for ao in ao_list:
            module = ao.name
            description = ao.description
            if isinstance(module, bytes):
                module = module.decode()
            if isinstance(description, bytes):
                description = description.decode()

            devices = vlc_instance.audio_output_device_list_get(module)
            if devices:
                for dev in devices:
                    dev_id = dev.device
                    dev_desc = dev.description
                    if isinstance(dev_id, bytes):
                        dev_id = dev_id.decode()
                    if isinstance(dev_desc, bytes):
                        dev_desc = dev_desc.decode()
                    outputs.append(
                        {"label": dev_desc, "module": module, "device": dev_id}
                    )
            else:
                outputs.append(
                    {"label": description, "module": module, "device": None}
                )
    except Exception as exc:  # noqa: BLE001 – libvlc errors vary by platform/version
        print(f"Advertencia: no se pudieron enumerar los dispositivos de audio: {exc}")
    return outputs


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class PlayOnThereApp:
    """Controlador principal de la aplicación PlayOnThere."""

    MEDIA_FILETYPES = [
        (
            "Archivos multimedia",
            "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v "
            "*.mpg *.mpeg *.mp3 *.wav *.flac *.aac *.ogg *.m4a",
        ),
        (
            "Vídeo",
            "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg",
        ),
        ("Audio", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
        ("Todos los archivos", "*.*"),
    ]

    def __init__(self, root: tk.Tk, vlc_instance=None) -> None:
        self.root = root
        self.root.title("PlayOnThere")
        self.root.resizable(False, False)

        self._vlc = vlc_instance or vlc.Instance()
        self._player = self._vlc.media_player_new()
        self._video_window: VideoWindow | None = None
        self._is_dragging_slider = False

        self._screens = build_screen_list(get_monitors())
        if not self._screens:
            self._screens = [
                {
                    "label": "Pantalla principal (1920×1080)",
                    "x": 0,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                }
            ]

        self._audio_outputs = enumerate_audio_outputs(self._vlc)

        self._build_ui()
        self._schedule_ui_update()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 5}

        # ── File picker ──────────────────────────────────────────────
        file_frame = ttk.LabelFrame(self.root, text="Archivo multimedia", padding=10)
        file_frame.pack(fill=tk.X, **pad)

        self.file_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_var, width=52)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(
            file_frame, text="Examinar…", command=self._browse_file
        ).pack(side=tk.RIGHT)

        # ── Screen selector ──────────────────────────────────────────
        screen_frame = ttk.LabelFrame(
            self.root, text="Pantalla de reproducción", padding=10
        )
        screen_frame.pack(fill=tk.X, **pad)

        self.screen_var = tk.StringVar()
        self._screen_combo = ttk.Combobox(
            screen_frame,
            textvariable=self.screen_var,
            values=[s["label"] for s in self._screens],
            state="readonly",
            width=55,
        )
        self._screen_combo.pack(fill=tk.X)
        # Default: last screen (most likely a secondary display)
        self._screen_combo.current(len(self._screens) - 1)

        # ── Audio device selector ────────────────────────────────────
        audio_frame = ttk.LabelFrame(
            self.root, text="Dispositivo de sonido", padding=10
        )
        audio_frame.pack(fill=tk.X, **pad)

        self.audio_var = tk.StringVar()
        self._audio_combo = ttk.Combobox(
            audio_frame,
            textvariable=self.audio_var,
            values=[a["label"] for a in self._audio_outputs],
            state="readonly",
            width=55,
        )
        self._audio_combo.pack(fill=tk.X)
        self._audio_combo.current(0)

        # ── Volume ───────────────────────────────────────────────────
        vol_frame = ttk.Frame(self.root)
        vol_frame.pack(fill=tk.X, padx=10, pady=(4, 2))

        ttk.Label(vol_frame, text="Volumen:").pack(side=tk.LEFT)
        self._vol_var = tk.IntVar(value=100)
        ttk.Scale(
            vol_frame,
            from_=0,
            to=200,
            orient=tk.HORIZONTAL,
            variable=self._vol_var,
            command=self._on_volume_change,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._vol_label = ttk.Label(vol_frame, text="100%", width=5)
        self._vol_label.pack(side=tk.RIGHT)

        # ── Progress bar ─────────────────────────────────────────────
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=2)

        self._time_label = ttk.Label(progress_frame, text="0:00 / 0:00", width=14)
        self._time_label.pack(side=tk.LEFT)

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_slider = ttk.Scale(
            progress_frame,
            from_=0,
            to=1000,
            orient=tk.HORIZONTAL,
            variable=self._progress_var,
            command=self._on_progress_seek,
        )
        self._progress_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._progress_slider.bind("<ButtonPress-1>", self._on_slider_press)
        self._progress_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # ── Playback controls ─────────────────────────────────────────
        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(pady=8)

        self._play_btn = ttk.Button(
            ctrl_frame, text="▶  Reproducir", command=self._play, width=15
        )
        self._play_btn.pack(side=tk.LEFT, padx=5)

        self._pause_btn = ttk.Button(
            ctrl_frame,
            text="⏸  Pausar",
            command=self._pause,
            width=12,
            state=tk.DISABLED,
        )
        self._pause_btn.pack(side=tk.LEFT, padx=5)

        self._stop_btn = ttk.Button(
            ctrl_frame,
            text="⏹  Detener",
            command=self._stop,
            width=12,
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            ctrl_frame,
            text="⛶  Pantalla completa",
            command=self._toggle_fullscreen,
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        # ── Status bar ───────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Listo.")
        ttk.Label(
            self.root,
            textvariable=self._status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(6, 2),
        ).pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(2, 6))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar archivo multimedia",
            filetypes=self.MEDIA_FILETYPES,
        )
        if path:
            self.file_var.set(path)

    def _on_volume_change(self, value) -> None:
        vol = int(float(value))
        self._player.audio_set_volume(vol)
        self._vol_label.config(text=f"{vol}%")

    def _on_slider_press(self, _event) -> None:
        self._is_dragging_slider = True

    def _on_slider_release(self, _event) -> None:
        self._is_dragging_slider = False
        pos = self._progress_var.get() / 1000.0
        self._player.set_position(pos)

    def _on_progress_seek(self, value) -> None:
        if self._is_dragging_slider:
            pos = float(value) / 1000.0
            self._player.set_position(pos)

    # ------------------------------------------------------------------
    # Playback actions
    # ------------------------------------------------------------------

    def _selected_screen(self) -> dict:
        idx = self._screen_combo.current()
        return self._screens[max(0, min(idx, len(self._screens) - 1))]

    def _selected_audio(self) -> dict:
        idx = self._audio_combo.current()
        return self._audio_outputs[max(0, min(idx, len(self._audio_outputs) - 1))]

    def _play(self) -> None:
        filepath = self.file_var.get().strip()
        if not filepath:
            messagebox.showwarning(
                "Sin archivo",
                "Por favor selecciona un archivo multimedia primero.",
            )
            return
        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"El archivo no existe:\n{filepath}")
            return

        self._stop()

        screen = self._selected_screen()
        self._video_window = VideoWindow(
            screen["x"], screen["y"], screen["width"], screen["height"]
        )
        self._video_window.root.protocol("WM_DELETE_WINDOW", self._stop)

        media = self._vlc.media_new(filepath)
        self._player.set_media(media)

        # Embed VLC renderer into our Tk frame
        wid = self._video_window.get_window_id()
        if sys.platform.startswith("linux"):
            self._player.set_xwindow(wid)
        elif sys.platform == "win32":
            self._player.set_hwnd(wid)
        elif sys.platform == "darwin":
            self._player.set_nsobject(wid)

        # Audio device
        audio = self._selected_audio()
        if audio["module"]:
            self._player.audio_output_set(audio["module"])
            if audio["device"]:
                self._player.audio_output_device_set(audio["module"], audio["device"])

        self._player.audio_set_volume(self._vol_var.get())
        self._player.play()

        self._play_btn.config(state=tk.DISABLED)
        self._pause_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._status_var.set(f"Reproduciendo: {os.path.basename(filepath)}")

    def _pause(self) -> None:
        if self._player.is_playing():
            self._player.pause()
            self._pause_btn.config(text="▶  Reanudar")
            self._status_var.set("Pausado.")
        else:
            self._player.play()
            self._pause_btn.config(text="⏸  Pausar")
            filepath = self.file_var.get().strip()
            self._status_var.set(f"Reproduciendo: {os.path.basename(filepath)}")

    def _stop(self) -> None:
        self._player.stop()
        if self._video_window is not None:
            self._video_window.destroy()
            self._video_window = None

        self._play_btn.config(state=tk.NORMAL)
        self._pause_btn.config(state=tk.DISABLED, text="⏸  Pausar")
        self._stop_btn.config(state=tk.DISABLED)
        self._progress_var.set(0)
        self._time_label.config(text="0:00 / 0:00")
        self._status_var.set("Detenido.")

    def _toggle_fullscreen(self) -> None:
        if self._video_window and self._video_window.is_alive():
            self._video_window.toggle_fullscreen()

    # ------------------------------------------------------------------
    # Periodic UI refresh
    # ------------------------------------------------------------------

    def _schedule_ui_update(self) -> None:
        self._update_ui()

    def _update_ui(self) -> None:
        try:
            state = self._player.get_state()
            if state == vlc.State.Ended:
                self._stop()
            elif state in (vlc.State.Playing, vlc.State.Paused):
                if not self._is_dragging_slider:
                    pos = self._player.get_position()
                    self._progress_var.set(pos * 1000)
                current_ms = self._player.get_time()
                total_ms = self._player.get_length()
                self._time_label.config(
                    text=f"{format_time(current_ms)} / {format_time(total_ms)}"
                )
        except Exception as exc:  # noqa: BLE001
            # Non-fatal: VLC may not be ready yet or the window may be closing.
            print(f"[PlayOnThere] UI update warning: {exc}", file=sys.stderr)
        self.root.after(500, self._update_ui)

    # ------------------------------------------------------------------

    def on_close(self) -> None:
        """Cierra la aplicación limpiamente."""
        self._stop()
        self.root.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    app = PlayOnThereApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
