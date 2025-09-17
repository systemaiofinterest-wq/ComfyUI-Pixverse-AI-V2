# PixVerse_Unified_Node.py

import os
import requests
import json
import time
import uuid
import random
from pathlib import Path
from pixverse_ai_v2.plogin import *

# === NODO UNIFICADO DE COMFYUI ===
class PixVerseLoginGenT2VUnifiedNode:
    def __init__(self):
        self.cached_token = ""
        self.cached_credit = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Correo electrónico para iniciar sesión en PixVerse"
                }),
                "password": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "password": True,
                    "tooltip": "Contraseña de la cuenta PixVerse"
                }),
                "refresh_token": ("BOOLEAN", {
                    "default": True,
                    "label_on": "Actualizar Token",
                    "label_off": "Usar Caché",
                    "tooltip": "Activa para refrescar el token. Desactiva para usar el último token sin hacer login."
                }),
                "prompt": ("STRING", {
                    "default": "A beautiful sunset over the mountains",
                    "multiline": True,
                    "tooltip": "Describe el video que deseas generar"
                }),
                "model_version": (["v3.5", "v4", "v4.5", "v5"], {"default": "v5"}),
                "duration": ([5, 8], {"default": 5}),
                "quality": (["360p", "540p", "720p", "1080p"], {"default": "360p"}),
                "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
                "style_selected": (["Normal", "Anime", "Animación 3D", "Cómic", "Cyberpunk", "Arcilla"], {"default": "Normal"}),
                "camera_selected": ([
                    "Normal",
                    "Horizontal Izquierda", "Horizontal Derecha",
                    "Vertical Arriba", "Vertical Abajo",
                    "Movimiento de Grúa hacia Arriba", "Dolly Zoom",
                    "Acercar", "Alejar",
                    "Zoom Rápido Acercando", "Zoom Rápido Alejando",
                    "Zoom Suave Acercando", "Super Dolly Alejando",
                    "Toma de Rastreo Izquierdo", "Toma de Rastreo Derecho",
                    "Toma de Arco Izquierdo", "Toma de Arco Derecho",
                    "Toma Fija", "Ángulo de Cámara",
                    "Brazo Robótico", "Barrido Rápido"
                ], {"default": "Normal"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "seed_select": ("BOOLEAN", {"default": False, "label_on": "Fijo", "label_off": "Aleatorio"}),
                "generate": ("BOOLEAN", {"default": False, "label_on": "Generar", "label_off": "Detener"})
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("video_path", "video_url", "credit")
    FUNCTION = "run_unified_process"
    CATEGORY = "PixVerse"
    OUTPUT_NODE = True

    def login(self, username, password, refresh_token):
        if not refresh_token:
            print("[PixVerse] 🔴 Modo caché: no se realizará login. Usando token guardado.")
            return (self.cached_token, self.cached_credit)

        print("[PixVerse] ✅ Actualización de token activada. Iniciando sesión...")

        if not username or not password:
            print("[PixVerse] ❌ Usuario o contraseña vacíos. No se puede hacer login.")
            return (self.cached_token, self.cached_credit)

        token = iniciar_sesion(username, password)
        if token:
            credit = obtener_credit_package(token)
            print(f"[PixVerse] ✅ Login exitoso. Créditos: {credit}")
            self.cached_token = token
            self.cached_credit = credit
            return (token, credit)
        else:
            print("[PixVerse] ⚠️  Error al iniciar sesión. Manteniendo token anterior si existe.")
            return (self.cached_token, self.cached_credit)

    def run_unified_process(self, username, password, refresh_token, prompt, model_version, duration, quality, aspect_ratio,
                           style_selected, camera_selected, seed, seed_select, generate):

        if not generate:
            print("❌ Generación no activada.")
            credit_actualizado = self.cached_credit if self.cached_token else 0
            return {
                "ui": {"text": "Detenido"},
                "result": ("❌ Generación no activada.", "", credit_actualizado)
            }

        # Realizar login
        jwt_token, credit = self.login(username, password, refresh_token)
        
        if not jwt_token:
            print("❌ JWT Token no proporcionado.")
            return {
                "ui": {"text": "Sin token"},
                "result": ("❌ JWT Token no proporcionado.", "", 0)
            }

        # Mapeo de modelos
        model_map = {
            "v3.5": "v3.5",
            "v4": "v4",
            "v4.5": "v4.5",
            "v5": "v5"
        }
        model = model_map[model_version]

        # Mapeo de estilos
        style_ids = {
            "Normal": "normal",
            "Anime": "anime",
            "Animación 3D": "3d_animation",
            "Cómic": "comic",
            "Cyberpunk": "cyberpunk",
            "Arcilla": "clay"
        }
        style = style_ids.get(style_selected, "normal")

        # Mapeo de cámaras
        camera_ids = {
            "Normal": "normal",
            "Horizontal Izquierda": "horizontal_left",
            "Horizontal Derecha": "horizontal_right",
            "Vertical Arriba": "vertical_up",
            "Vertical Abajo": "vertical_down",
            "Movimiento de Grúa hacia Arriba": "crane_up",
            "Dolly Zoom": "hitchcock",
            "Acercar": "zoom_in",
            "Alejar": "zoom_out",
            "Zoom Rápido Acercando": "quickly_zoom_in",
            "Zoom Rápido Alejando": "quickly_zoom_out",
            "Zoom Suave Acercando": "smooth_zoom_in",
            "Super Dolly Alejando": "super_dolly_out",
            "Toma de Rastreo Izquierdo": "left_follow",
            "Toma de Rastreo Derecho": "right_follow",
            "Toma de Arco Izquierdo": "pan_left",
            "Toma de Arco Derecho": "pan_right",
            "Toma Fija": "fix_bg",
            "Ángulo de Cámara": "camera_rotation",
            "Brazo Robótico": "robo_arm",
            "Barrido Rápido": "whip_pan"
        }
        camera_movement = camera_ids.get(camera_selected, "normal")

        # Validar combinación
        valido, creditos_necesarios = validar_combinacion(model, duration, quality)
        if not valido:
            msg = f"❌ Combinación no válida: {model} | {duration}s | {quality}"
            credit_actualizado = obtener_credit_package(jwt_token)
            self.cached_credit = credit_actualizado
            return {
                "ui": {"text": "Error"},
                "result": (msg, "", credit_actualizado)
            }

        creditos_actuales = obtener_credit_package(jwt_token)
        if creditos_necesarios > creditos_actuales:
            msg = f"❌ Créditos insuficientes: {creditos_actuales}/{creditos_necesarios}"
            self.cached_credit = creditos_actuales
            return {
                "ui": {"text": "Créditos insuf."},
                "result": (msg, "", creditos_actuales)
            }

        print(f"✅ Créditos suficientes: {creditos_actuales}/{creditos_necesarios}")

        # 🚀 Generar video
        video_id = send_pixverse_request(
            token=jwt_token,
            prompt=prompt,
            model=model,
            duration=duration,
            quality=quality,
            aspect_ratio=aspect_ratio,
            style=style,
            seed=seed if seed_select else 0,
            camera_movement=camera_movement,
            credit_change=creditos_necesarios
        )

        if not video_id or isinstance(video_id, str) and ("Créditos agotados" in video_id or "Parámetro inválido" in video_id):
            print(f"❌ Error al generar video: {video_id}")
            credit_actualizado = obtener_credit_package(jwt_token)
            self.cached_credit = credit_actualizado
            return {
                "ui": {"text": "Error gen."},
                "result": (f"❌ Error: {video_id}", "", credit_actualizado)
            }

        print(f"🎥 Video iniciado: {video_id}")
        os.environ["VIDEO_ID"] = str(video_id)
        os.environ["PROMPT"] = prompt

        # Asegurar directorio de salida
        comfy_output_dir = Path("output") / "Pixverse"
        comfy_output_dir.mkdir(parents=True, exist_ok=True)

        # ✅ Polling y descarga
        result = poll_for_specific_video_txt(jwt_token, video_id, prompt, str(comfy_output_dir))
        if result:
            video_path, video_url = result
            credit_actualizado = obtener_credit_package(jwt_token)
            self.cached_credit = credit_actualizado
            return {
                "ui": {"text": f"Listo: {os.path.basename(video_path)}"},
                "result": (video_path, video_url, credit_actualizado)
            }
        else:
            credit_actualizado = obtener_credit_package(jwt_token)
            self.cached_credit = credit_actualizado
            return {
                "ui": {"text": "Error descarga"},
                "result": ("❌ Error al descargar el video.", "", credit_actualizado)
            }

