# PixVerse_Video_Extension_Complete.py

import os
import requests
import uuid
import time
import oss2
import cv2
from urllib.parse import unquote
import json
import tempfile
import shutil
from pathlib import Path
from pixverse_ai_v2.plogin import *

# === NODO UNIFICADO DE COMFYUI PARA EXTENSIÓN DE VIDEO ===
class PixVerseLoginGenExtendUnifiedNode:
    def __init__(self):
        self.cached_token = ""
        self.cached_credit = 0
        self.temp_dir = tempfile.gettempdir()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Login parameters
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
                # Video parameters
                "video_path": ("STRING", {
                    "forceInput": True,
                    "tooltip": "Ruta del video local (de un nodo anterior)"
                }),
                "upload_video": ("BOOLEAN", {
                    "default": True,
                    "label_on": "Subir Video",
                    "label_off": "No Subir"
                }),
                # Extension parameters
                "prompt": ("STRING", {
                    "default": "Continue the scene with dynamic movement",
                    "multiline": True,
                    "tooltip": "Prompt para extender el video"
                }),
                "model_version": (["v3.5", "v4", "v4.5", "v5"], {"default": "v5"}),
                "duration": ([5, 8], {"default": 5}),
                "quality": (["360p", "540p", "720p", "1080p"], {"default": "360p"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "use_custom_seed": ("BOOLEAN", {"default": False}),
                "extend": ("BOOLEAN", {"default": False, "label_on": "Extender", "label_off": "Detener"})
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("video_path", "video_url", "credit")
    FUNCTION = "run_video_extension_complete"
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

    def upload_video_internal(self, video_path, jwt_token):
        """Sube el video local a PixVerse y devuelve datos necesarios."""
        if not jwt_token:
            return {"success": False, "error": "JWT Token no proporcionado"}

        if not os.path.exists(video_path):
            return {"success": False, "error": "Archivo de video no encontrado", "jwt_token": jwt_token}

        duration = obtener_segundos_video(video_path)
        if not duration:
            return {"success": False, "error": "No se pudo obtener la duración del video", "jwt_token": jwt_token}

        print(f"🎥 Video detectado: {video_path} | Duración: {duration}s")

        creditos = obtener_credit_package(jwt_token)
        if creditos < 20:
            return {"success": False, "error": f"Créditos insuficientes para subir video: {creditos}/20", "jwt_token": jwt_token}

        print(f"✅ Créditos disponibles: {creditos}")

        # Obtener token de subida
        token_data = get_upload_token(jwt_token)
        if not token_data:
            return {"success": False, "error": "Error al obtener token de subida", "jwt_token": jwt_token}

        # Subir a OSS
        media_path, _ = upload_video_to_oss(video_path, token_data)
        if not media_path:
            return {"success": False, "error": "Error al subir a OSS", "jwt_token": jwt_token}

        # Confirmar en PixVerse
        uploaded_final_url = confirm_upload_on_pixverse_video(media_path, jwt_token)
        if not uploaded_final_url:
            return {"success": False, "error": "Error al confirmar en PixVerse", "jwt_token": jwt_token}

        # Obtener último fotograma
        last_frame_url = get_last_frame(jwt_token, media_path, duration)
        if not last_frame_url:
            print("⚠️ No se pudo obtener el último fotograma.")

        return {
            "success": True,
            "media_path": media_path,
            "uploaded_final_url": uploaded_final_url,
            "last_frame_url": last_frame_url or "",
            "duration_seconds": duration,
            "jwt_token": jwt_token
        }

    def extend_video_internal(self, prompt, model_version, duration, quality, seed, use_custom_seed,
                             jwt_token, media_path, uploaded_final_url, last_frame_url, duration_seconds):
        """Extiende el video usando los datos proporcionados."""
        if not jwt_token:
            return {"success": False, "error": "❌ JWT Token no proporcionado."}

        if not media_path or not uploaded_final_url or not last_frame_url:
            return {"success": False, "error": "❌ Faltan datos del video subido."}

        # Mapeo de modelos
        model_map = {
            "v3.5": "v3.5",
            "v4": "v4",
            "v4.5": "v4.5",
            "v5": "v5"
        }
        model = model_map[model_version]

        # Validar combinación
        valido, creditos = validar_combinacion(model, duration, quality)
        if not valido:
            msg = f"❌ Combinación no válida: {model} | {duration}s | {quality}"
            return {"success": False, "error": msg}

        creditos_paquete = obtener_credit_package(jwt_token)
        if creditos > creditos_paquete:
            msg = f"❌ Créditos insuficientes: {creditos_paquete}/{creditos}"
            return {"success": False, "error": msg}

        print(f"✅ Créditos suficientes: {creditos_paquete}/{creditos}")

        # Calcular credit_change
        credit_change = min(((duration_seconds + 4) // 5) * 10, 60)

        # Extender video
        print("🚀 Extendiendo video...")
        video_id = extend_pixverse_video(
            token=jwt_token,
            prompt=prompt,
            model=model,
            duration=duration,
            quality=quality,
            seed=seed if use_custom_seed else 0,
            credit_change=credit_change,
            customer_video_path=media_path,
            customer_video_url=uploaded_final_url,
            customer_video_duration=duration_seconds,
            customer_video_last_frame_url=last_frame_url
        )

        if not video_id or "Créditos agotados" in str(video_id) or "Parámetro inválido" in str(video_id):
            return {"success": False, "error": f"❌ Error al extender video: {video_id}"}

        print(f"🎥 Video extendido iniciado: {video_id}")
        os.environ["VIDEO_ID"] = str(video_id)
        os.environ["PROMPT"] = prompt
        comfy_output_dir = Path("output") / "Pixverse"
        comfy_output_dir.mkdir(parents=True, exist_ok=True)
        # Polling y descarga
        result = poll_for_specific_video_txt(jwt_token, video_id, prompt, str(comfy_output_dir))
        if result:
            video_path, video_url = result
            credit_actualizado = obtener_credit_package(jwt_token)
            return {
                "success": True,
                "video_path": video_path,
                "video_url": video_url,
                "credit": credit_actualizado
            }
        else:
            return {"success": False, "error": "❌ Error al descargar el video extendido."}

    def run_video_extension_complete(self, username, password, refresh_token, 
                                   video_path, upload_video, prompt, model_version, duration, 
                                   quality, seed, use_custom_seed, extend):

        if not extend:
            credit_actualizado = self.cached_credit if self.cached_token else 0
            return {
                "ui": {"text": "Extensión desactivada"},
                "result": ("❌ Extensión no activada.", "", credit_actualizado)
            }

        # Realizar login
        jwt_token, credit = self.login(username, password, refresh_token)
        
        if not jwt_token:
            return {
                "ui": {"text": "Token faltante"},
                "result": ("❌ JWT Token no proporcionado.", "", 0)
            }

        # Subir video si está activado
        if upload_video:
            upload_result = self.upload_video_internal(video_path, jwt_token)
            if not upload_result.get("success"):
                error_msg = upload_result.get("error", "Error desconocido al subir video")
                jwt_token = upload_result.get("jwt_token", jwt_token)
                credit_actualizado = obtener_credit_package(jwt_token)
                return {
                    "ui": {"text": "Error subida"},
                    "result": (error_msg, "", credit_actualizado)
                }

            media_path = upload_result["media_path"]
            uploaded_final_url = upload_result["uploaded_final_url"]
            last_frame_url = upload_result["last_frame_url"]
            duration_seconds = upload_result["duration_seconds"]
            jwt_token = upload_result["jwt_token"]
        else:
            # Si no se sube video, no se puede extender
            return {
                "ui": {"text": "Sin video"},
                "result": ("❌ Se requiere video subido para extender.", "", credit)
            }

        # Extender video
        extend_result = self.extend_video_internal(
            prompt, model_version, duration, quality, seed, use_custom_seed,
            jwt_token, media_path, uploaded_final_url, last_frame_url, duration_seconds
        )

        if not extend_result.get("success"):
            error_msg = extend_result.get("error", "Error desconocido al extender video")
            credit_actualizado = obtener_credit_package(jwt_token)
            return {
                "ui": {"text": "Error extensión"},
                "result": (error_msg, "", credit_actualizado)
            }

        video_path_result = extend_result["video_path"]
        video_url = extend_result["video_url"]
        credit_final = extend_result["credit"]

        return {
            "ui": {"text": f"Listo: {os.path.basename(video_path_result)}"},
            "result": (video_path_result, video_url, credit_final)
        }
