"""
╔══════════════════════════════════════════════════════════════════╗
║       SISTEMA DE DETECCIÓN DE COLORES DE ROPA EN VIDEO          ║
║       OpenCV + YOLOv8 + K-Means Clustering + yt-dlp            ║
╚══════════════════════════════════════════════════════════════════╝

Descripción:
    Detecta personas en video, analiza los colores dominantes
    de su ropa usando K-Means clustering y genera estadísticas
    en tiempo real con reporte final detallado.

Uso:
    # Video de YouTube
    python clothing_color.py --youtube "https://www.youtube.com/watch?v=VIDEO_ID"

    # Video local
    python clothing_color.py --video "mi_video.mp4"

    # Opciones avanzadas
    python clothing_color.py --video "video.mp4" --conf 0.5 --skip 2 --colores 3

Instalación:
    pip install ultralytics scikit-learn yt-dlp opencv-python numpy
"""

import cv2
import argparse
import sys
import time
import os
import numpy as np
from collections import defaultdict

# ── Fix para Linux: evitar múltiples ventanas ──
os.environ.setdefault("DISPLAY", ":0")

# ──────────────────────────────────────────────
#  Verificar dependencias
# ──────────────────────────────────────────────
try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] ultralytics no está instalado.")
    print("  Ejecutá: pip install ultralytics")
    sys.exit(1)

try:
    from sklearn.cluster import KMeans
except ImportError:
    print("[ERROR] scikit-learn no está instalado.")
    print("  Ejecutá: pip install scikit-learn")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("[ERROR] yt-dlp no está instalado.")
    print("  Ejecutá: pip install yt-dlp")
    sys.exit(1)


# ══════════════════════════════════════════════
#  CONFIGURACIÓN DE COLORES
# ══════════════════════════════════════════════

# Colores base en HSV para clasificación
# Formato: nombre → [(H_min, H_max, S_min, V_min)]
COLOR_RANGES = {
    "Rojo":     [(0,   10,  80, 50), (160, 180, 80, 50)],
    "Naranja":  [(10,  25,  80, 50)],
    "Amarillo": [(25,  35,  80, 50)],
    "Verde":    [(35,  85,  50, 50)],
    "Cian":     [(85,  100, 50, 50)],
    "Azul":     [(100, 130, 50, 50)],
    "Violeta":  [(130, 160, 50, 50)],
    "Rosa":     [(160, 180, 30, 150)],
    "Blanco":   [(0,   180, 0,  200)],
    "Gris":     [(0,   180, 0,  80)],
    "Negro":    [(0,   180, 0,  0)],
}

# Colores BGR para visualización en pantalla
DISPLAY_COLORS = {
    "Rojo":     (0,   0,   220),
    "Naranja":  (0,   140, 255),
    "Amarillo": (0,   220, 220),
    "Verde":    (0,   180,  50),
    "Cian":     (200, 200,   0),
    "Azul":     (220,  80,   0),
    "Violeta":  (200,   0, 180),
    "Rosa":     (180,  80, 220),
    "Blanco":   (240, 240, 240),
    "Gris":     (140, 140, 140),
    "Negro":    ( 60,  60,  60),
    "Mixto":    (180, 180, 180),
}

# Clase COCO para persona
PERSON_CLASS = 0


# ══════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ══════════════════════════════════════════════

def get_youtube_stream(url: str) -> str:
    """Extrae la URL directa del stream de YouTube."""
    print(f"[INFO] Obteniendo stream de YouTube...")
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"[INFO] Video: {info.get('title', 'Sin título')}")
            duration = info.get('duration', 0)
            print(f"[INFO] Duración: {duration // 60}m {duration % 60}s")
            return info['url']
    except Exception as e:
        print(f"[ERROR] No se pudo obtener el stream: {e}")
        print("  Intentá actualizar yt-dlp: pip install -U yt-dlp")
        sys.exit(1)


def open_video(args) -> cv2.VideoCapture:
    """Abre la fuente de video según los argumentos."""
    if args.youtube:
        stream_url = get_youtube_stream(args.youtube)
        cap = cv2.VideoCapture(stream_url)
    elif args.video:
        cap = cv2.VideoCapture(args.video)
    else:
        print("[ERROR] Especificá --youtube o --video")
        sys.exit(1)

    if not cap.isOpened():
        print("[ERROR] No se pudo abrir el video.")
        sys.exit(1)

    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Resolución: {width}x{height} | FPS: {fps:.1f}")
    return cap


def classify_color_hsv(bgr_color) -> str:
    """
    Clasifica un color BGR en una categoría de color usando HSV.
    Primero detecta negro, blanco y gris por valor/saturación,
    luego clasifica por tono (hue).
    """
    pixel = np.uint8([[bgr_color]])
    hsv   = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

    # Negro
    if v < 40:
        return "Negro"
    # Blanco
    if s < 30 and v > 180:
        return "Blanco"
    # Gris
    if s < 40:
        return "Gris"
    # Rojo (wrap-around en HSV)
    if h < 10 or h > 160:
        return "Rojo"
    if 10 <= h < 25:
        return "Naranja"
    if 25 <= h < 35:
        return "Amarillo"
    if 35 <= h < 85:
        return "Verde"
    if 85 <= h < 100:
        return "Cian"
    if 100 <= h < 130:
        return "Azul"
    if 130 <= h < 160:
        return "Violeta"

    return "Mixto"


def extract_dominant_colors(roi, n_colors: int = 3):
    """
    Extrae los N colores dominantes de una región de imagen
    usando K-Means clustering.
    Retorna lista de (color_BGR, porcentaje, nombre_color).
    """
    if roi is None or roi.size == 0:
        return []

    # Redimensionar para velocidad
    small = cv2.resize(roi, (60, 60))
    pixels = small.reshape(-1, 3).astype(np.float32)

    # Filtrar píxeles muy oscuros (sombras/fondo)
    mask = np.any(pixels > 20, axis=1)
    pixels = pixels[mask]

    if len(pixels) < n_colors:
        return []

    try:
        kmeans = KMeans(n_clusters=n_colors, n_init=3, max_iter=100, random_state=42)
        kmeans.fit(pixels)
        labels   = kmeans.labels_
        centers  = kmeans.cluster_centers_.astype(int)
        counts   = np.bincount(labels)
        total    = counts.sum()

        resultado = []
        for i in np.argsort(-counts):  # Ordenar por frecuencia
            bgr        = tuple(centers[i])
            porcentaje = counts[i] / total * 100
            nombre     = classify_color_hsv(bgr)
            resultado.append((bgr, porcentaje, nombre))
        return resultado

    except Exception:
        return []


def get_torso_roi(frame, x1, y1, x2, y2):
    """
    Extrae la región del torso de una persona (zona media),
    evitando cabeza y piernas para mejor análisis de ropa.
    """
    h = y2 - y1
    w = x2 - x1

    # Torso: del 25% al 65% de la altura, con margen lateral
    torso_y1 = y1 + int(h * 0.25)
    torso_y2 = y1 + int(h * 0.65)
    torso_x1 = x1 + int(w * 0.10)
    torso_x2 = x2 - int(w * 0.10)

    # Validar límites
    torso_y1 = max(0, torso_y1)
    torso_y2 = min(frame.shape[0], torso_y2)
    torso_x1 = max(0, torso_x1)
    torso_x2 = min(frame.shape[1], torso_x2)

    if torso_y2 <= torso_y1 or torso_x2 <= torso_x1:
        return None

    return frame[torso_y1:torso_y2, torso_x1:torso_x2]


def draw_person_box(frame, x1, y1, x2, y2, colors_info, person_id):
    """Dibuja el bounding box de la persona con sus colores detectados."""
    # Color principal del borde = color dominante detectado
    main_color_name = colors_info[0][2] if colors_info else "Mixto"
    border_color    = DISPLAY_COLORS.get(main_color_name, (0, 255, 0))

    # Rectángulo principal
    cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2, cv2.LINE_AA)

    # Etiqueta con ID
    label = f"#{person_id} {main_color_name}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), border_color, -1)
    cv2.putText(frame, label, (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    # Mini paleta de colores debajo del box
    swatch_w = (x2 - x1) // len(colors_info) if colors_info else 0
    for i, (bgr, pct, nombre) in enumerate(colors_info):
        sx1 = x1 + i * swatch_w
        sx2 = sx1 + swatch_w
        cv2.rectangle(frame, (sx1, y2), (sx2, y2 + 10), tuple(int(c) for c in bgr), -1)


def draw_dashboard(frame, color_stats, person_count, fps_real, frame_num):
    """
    Dibuja el panel principal de estadísticas en la esquina
    superior izquierda con barras de progreso por color.
    """
    panel_w = 300
    n_colors = len(color_stats)
    panel_h  = 55 + n_colors * 26 + 40
    overlay  = frame.copy()

    cv2.rectangle(overlay, (8, 8), (8 + panel_w, 8 + panel_h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    # Título
    cv2.putText(frame, "ANALISIS DE COLOR DE ROPA", (18, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 180), 2, cv2.LINE_AA)

    # Subtítulo
    cv2.putText(frame, f"Personas detectadas: {person_count}  |  Frame: {frame_num}",
                (18, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1, cv2.LINE_AA)

    # Barras por color
    y = 72
    total_detecciones = sum(color_stats.values()) or 1
    for nombre, cantidad in sorted(color_stats.items(), key=lambda x: -x[1]):
        pct        = cantidad / total_detecciones * 100
        bar_len    = int((panel_w - 120) * pct / 100)
        color_bgr  = DISPLAY_COLORS.get(nombre, (180, 180, 180))

        # Nombre del color
        cv2.putText(frame, f"{nombre:<10}", (18, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, color_bgr, 1, cv2.LINE_AA)

        # Barra de progreso
        cv2.rectangle(frame, (105, y - 10), (105 + bar_len, y - 1), color_bgr, -1)

        # Porcentaje
        cv2.putText(frame, f"{pct:.0f}%", (105 + bar_len + 4, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)
        y += 26

    # FPS
    cv2.putText(frame, f"FPS: {fps_real:.1f}", (18, y + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 100, 100), 1, cv2.LINE_AA)


def draw_color_palette(frame, color_stats):
    """
    Dibuja una paleta de colores acumulada en la esquina
    inferior derecha del frame.
    """
    if not color_stats:
        return

    h, w = frame.shape[:2]
    swatch_size = 35
    margin      = 10
    total       = sum(color_stats.values()) or 1

    colores_ordenados = sorted(color_stats.items(), key=lambda x: -x[1])[:8]
    palette_w = len(colores_ordenados) * (swatch_size + 4) + margin * 2
    palette_h = swatch_size + 30

    px1 = w - palette_w - margin
    py1 = h - palette_h - margin

    overlay = frame.copy()
    cv2.rectangle(overlay, (px1 - 5, py1 - 5),
                  (w - margin + 5, h - margin + 5), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, "Paleta acumulada", (px1, py1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)

    x = px1
    for nombre, cantidad in colores_ordenados:
        pct       = cantidad / total * 100
        color_bgr = DISPLAY_COLORS.get(nombre, (180, 180, 180))
        cv2.rectangle(frame, (x, py1), (x + swatch_size, py1 + swatch_size),
                      color_bgr, -1)
        cv2.putText(frame, f"{pct:.0f}%", (x, py1 + swatch_size + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, color_bgr, 1, cv2.LINE_AA)
        x += swatch_size + 4


def print_final_report(color_stats_total, person_ids_total, total_frames, elapsed):
    """Imprime el reporte final detallado en consola."""
    print("\n" + "═" * 55)
    print("        REPORTE FINAL — ANÁLISIS DE COLOR DE ROPA")
    print("═" * 55)

    total = sum(color_stats_total.values()) or 1
    print(f"\n  Personas únicas detectadas : {len(person_ids_total)}")
    print(f"  Frames procesados          : {total_frames}")
    print(f"  Tiempo total               : {elapsed:.1f} segundos\n")

    print("  DISTRIBUCIÓN DE COLORES:")
    print("  " + "─" * 45)

    for nombre, cantidad in sorted(color_stats_total.items(), key=lambda x: -x[1]):
        pct   = cantidad / total * 100
        barra = "█" * int(pct / 3)
        print(f"  {nombre:<12} {cantidad:>5} detecciones  {barra} {pct:.1f}%")

    print("\n  COLOR MÁS COMÚN: " +
          max(color_stats_total, key=color_stats_total.get, default="N/A").upper())
    print("═" * 55 + "\n")


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Detección de colores de ropa en video con YOLOv8 + K-Means"
    )
    parser.add_argument('--youtube', help='URL de YouTube')
    parser.add_argument('--video',   help='Ruta a video local')
    parser.add_argument('--conf',    type=float, default=0.45,
                        help='Confianza mínima de detección (default: 0.45)')
    parser.add_argument('--skip',    type=int,   default=2,
                        help='Procesar 1 de cada N frames (default: 2)')
    parser.add_argument('--colores', type=int,   default=3,
                        help='Número de colores dominantes a extraer por persona (default: 3)')
    parser.add_argument('--modelo',  default='yolov8n.pt',
                        help='Modelo YOLO (default: yolov8n.pt)')
    parser.add_argument('--ancho',   type=int,   default=720,
                        help='Ancho máximo del frame para procesar (default: 720)')
    parser.add_argument('--maxpers', type=int,   default=10,
                        help='Máximo de personas a procesar por frame (default: 10)')
    args = parser.parse_args()

    # ── Cargar modelo ─────────────────────────────
    print(f"[INFO] Cargando modelo {args.modelo}...")
    try:
        model = YOLO(args.modelo)
        print("[INFO] Modelo cargado correctamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el modelo: {e}")
        sys.exit(1)

    # ── Abrir video ───────────────────────────────
    video = open_video(args)
    print(f"[INFO] Iniciando análisis. Presioná 'q' para salir.\n")

    # ── Inicializar ventana UNA sola vez ──────────
    WINDOW_NAME = "Deteccion de Color de Ropa"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 900, 540)

    # ── Variables de estado ───────────────────────
    color_stats_frame = defaultdict(int)
    color_stats_total = defaultdict(int)
    person_ids_total  = set()
    frame_count       = 0
    processed         = 0
    start_time        = time.time()

    while True:
        has_frame, frame = video.read()
        if not has_frame:
            print("[INFO] Fin del video.")
            break

        frame_count += 1
        if frame_count % args.skip != 0:
            continue

        processed += 1
        color_stats_frame.clear()

        # ── Redimensionar frame para aliviar CPU ──
        h_orig, w_orig = frame.shape[:2]
        if w_orig > args.ancho:
            scale = args.ancho / w_orig
            frame = cv2.resize(frame, (args.ancho, int(h_orig * scale)))

        # ── Detección de personas ─────────────────
        results = model.track(
            frame,
            persist=True,
            conf=args.conf,
            classes=[PERSON_CLASS],
            verbose=False,
            tracker="bytetrack.yaml"
        )

        person_count = 0

        if results[0].boxes is not None:
            boxes = results[0].boxes.data.tolist()
            # Limitar cantidad de personas por frame
            boxes = boxes[:args.maxpers]

            for box in boxes:
                x1, y1, x2, y2 = map(int, box[:4])
                track_id = int(box[4]) if len(box) > 6 else -1

                if track_id != -1:
                    person_ids_total.add(track_id)

                person_count += 1

                torso = get_torso_roi(frame, x1, y1, x2, y2)
                colors_info = extract_dominant_colors(torso, args.colores)

                for bgr, pct, nombre in colors_info:
                    color_stats_frame[nombre] += 1
                    color_stats_total[nombre] += 1

                draw_person_box(frame, x1, y1, x2, y2, colors_info, track_id)

        # ── Dashboard y paleta ────────────────────
        elapsed  = time.time() - start_time
        fps_real = processed / elapsed if elapsed > 0 else 0

        draw_dashboard(frame, color_stats_total, person_count, fps_real, frame_count)
        draw_color_palette(frame, color_stats_total)

        # ── Mostrar en la MISMA ventana siempre ───
        cv2.imshow(WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] Saliendo por solicitud del usuario.")
            break

    # ── Reporte final ─────────────────────────────
    elapsed = time.time() - start_time
    video.release()
    cv2.destroyAllWindows()
    print_final_report(dict(color_stats_total), person_ids_total, processed, elapsed)


if __name__ == "__main__":
    main()
