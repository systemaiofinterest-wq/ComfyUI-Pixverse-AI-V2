# PixVerse_Unified_Workflow.py

import os
import requests
import uuid
import time
import oss2
from urllib.parse import unquote
from torchvision.transforms import ToPILImage
import tempfile
import json
import shutil
from pathlib import Path
from pixverse_ai_v2.plogin import *

# === NODO UNIFICADO DE COMFYUI ===
class PixVerseLoginGenI2VUnifiedNode:
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
                # Image parameters
                "image": ("IMAGE",),
                "upload_image": ("BOOLEAN", {
                    "default": True,
                    "label_on": "Subir Imagen",
                    "label_off": "No Subir"
                }),
                # Video generation parameters
                "prompt": ("STRING", {
                    "default": "A cat dancing in the rain",
                    "multiline": True,
                    "tooltip": "Describe el video que quieres generar"
                }),
                "quality": (["360p", "540p", "720p", "1080p"], {"default": "360p"}),
                "model_version": (["v3.5", "v4", "v4.5", "v5"], {"default": "v5"}),
                "motion_mode": (["normal"], {"default": "normal"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "seed_select": ("BOOLEAN", {"default": False, "label_on": "Fijo", "label_off": "Aleatorio"}),
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
                "duration": ([5, 8], {"default": 5}),
                "generate": ("BOOLEAN", {"default": False, "label_on": "Generar", "label_off": "Detener"})
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("video_path", "video_url", "credit")
    FUNCTION = "run_unified_workflow"
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

    def upload_image_internal(self, image, jwt_token):
        """Sube la imagen y devuelve el JSON con los datos necesarios."""
        if not jwt_token:
            return {"success": False, "error": "JWT Token no proporcionado"}

        try:
            to_pil = ToPILImage()
            temp_path = os.path.join(self.temp_dir, f"pixverse_upload_{uuid.uuid4().hex}.png")

            if len(image.shape) == 4:
                image = image[0]

            pil_image = to_pil(image.permute(2, 0, 1).cpu())
            pil_image.save(temp_path, format='PNG')
            print(f"🖼️ Imagen temporal guardada: {temp_path}")
        except Exception as e:
            return {"success": False, "error": f"Error al procesar imagen: {str(e)}"}

        creditos = obtener_credit_package(jwt_token)
        if creditos < 20:
            return {"success": False, "error": f"Créditos insuficientes para subir imagen: {creditos}/20"}

        print(f"✅ Créditos disponibles para subir: {creditos}")

        token_data = get_upload_token(jwt_token)
        if not token_data:
            return {"success": False, "error": "Error al obtener token de subida"}

        media_path, _ = upload_image_to_oss(temp_path, token_data)
        if not media_path:
            return {"success": False, "error": "Error al subir a OSS"}

        size = os.path.getsize(temp_path)
        uploaded_final_url = confirm_upload_on_pixverse(
            path=media_path,
            name=os.path.basename(media_path),
            size=size,
            token_header=jwt_token
        )

        try:
            os.remove(temp_path)
        except Exception as e:
            print(f"⚠️ No se pudo eliminar temporal: {e}")

        if uploaded_final_url:
            return {
                "success": True,
                "jwt_token": jwt_token,
                "uploaded_final_url": uploaded_final_url,
                "media_path": media_path,
                "duration_seconds": 5,
                "last_frame_url": uploaded_final_url,
                "error": None
            }
        else:
            return {"success": False, "error": "Error al confirmar en PixVerse"}

    def run_unified_workflow(self, username, password, refresh_token, image, upload_image, 
                           prompt, quality, model_version, motion_mode, seed, seed_select, 
                           style_selected, camera_selected, duration, generate):

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

        # Subir imagen si está activado
        if upload_image:
            upload_result = self.upload_image_internal(image, jwt_token)
            if not upload_result.get("success"):
                error_msg = f"❌ Error al subir imagen: {upload_result.get('error', 'Desconocido')}"
                credit_actualizado = obtener_credit_package(jwt_token)
                return {
                    "ui": {"text": "Error subida"},
                    "result": (error_msg, "", credit_actualizado)
                }

            uploaded_final_url = upload_result.get("uploaded_final_url", "")
            media_path = upload_result.get("media_path", "")
            jwt_token = upload_result.get("jwt_token", jwt_token)
        else:
            # Si no se sube imagen, no se puede generar video desde imagen
            return {
                "ui": {"text": "Sin imagen"},
                "result": ("❌ Se requiere imagen para generar video.", "", credit)
            }

        # Verificar datos de subida
        if not all([jwt_token, uploaded_final_url, media_path]):
            print("❌ Datos faltantes en upload_data")
            credit_actualizado = obtener_credit_package(jwt_token) if jwt_token else 0
            return {
                "ui": {"text": "Faltan datos"},
                "result": ("❌ Datos faltantes en upload_data", "", credit_actualizado)
            }

        # Obtener créditos actuales
        credit_actualizado = obtener_credit_package(jwt_token)

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
            return {
                "ui": {"text": "Error"},
                "result": (msg, "", credit_actualizado)
            }

        if creditos_necesarios > credit_actualizado:
            msg = f"❌ Créditos insuficientes: {credit_actualizado}/{creditos_necesarios}"
            return {
                "ui": {"text": "Créditos insuf."},
                "result": (msg, "", credit_actualizado)
            }

        print(f"✅ Créditos suficientes: {credit_actualizado}/{creditos_necesarios}")

        # 🚀 Generar video
        video_id = generate_video_from_image(
            media_path=media_path,
            media_url=uploaded_final_url,
            prompt=prompt,
            duration=duration,
            quality=quality,
            token=jwt_token,
            model=model,
            credit_change=creditos_necesarios,
            style=style,
            camera_movement=camera_movement,
            seed=seed if seed_select else 0,
            motion_mode=motion_mode
        )

        if not video_id or isinstance(video_id, str) and ("Créditos agotados" in video_id or "Parámetro inválido" in video_id):
            print(f"❌ Error al generar video: {video_id}")
            credit_actualizado = obtener_credit_package(jwt_token)
            return {
                "ui": {"text": "Error gen."},
                "result": (f"❌ Error: {video_id}", "", credit_actualizado)
            }

        print(f"🎥 Video iniciado: {video_id}")
        os.environ["VIDEO_ID"] = str(video_id)
        comfy_output_dir = Path("output") / "Pixverse"
        comfy_output_dir.mkdir(parents=True, exist_ok=True)
        # ✅ Polling y descarga
        result = poll_for_specific_video(jwt_token, video_id, str(comfy_output_dir))
        if result:
            video_path, video_url = result
            credit_actualizado = obtener_credit_package(jwt_token)
            return {
                "ui": {"text": f"Listo: {os.path.basename(video_path)}"},
                "result": (video_path, video_url, credit_actualizado)
            }
        else:
            credit_actualizado = obtener_credit_package(jwt_token)
            return {
                "ui": {"text": "Error descarga"},
                "result": ("❌ Error al descargar el video.", "", credit_actualizado)
            }

