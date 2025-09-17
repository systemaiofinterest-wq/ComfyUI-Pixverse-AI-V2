# ComfyUI-Pixverse-AI-V2
# Creado por IA(Sistema de Interes)
# 1. Visit [Youtube Channel](https://www.youtube.com/@IA.Sistema.de.Interes)
#Update: 17/09/25 En esta nueva actualización simplifiqué los nodos en uno solo para cada generación, eliminando las conexiones y errores

Este es un entorno de trabajo no oficial, que esta diseñado para ahorras costos de generacion de videos por IA, utilizando la latafroma Pixverse, como todos sabemos el costo de generar un video tilizando la API

<img width="1502" height="510" alt="image" src="https://raw.githubusercontent.com/systemaiofinterest-wq/ComfyUI-Pixverse-AI-V2/refs/heads/main/t2v.png" />

<img width="1502" height="510" alt="image" src="https://raw.githubusercontent.com/systemaiofinterest-wq/ComfyUI-Pixverse-AI-V2/refs/heads/main/i2v.png" />

<img width="1502" height="510" alt="image" src="https://raw.githubusercontent.com/systemaiofinterest-wq/ComfyUI-Pixverse-AI-V2/refs/heads/main/extend.png" />


Si usamos la API de comfyUI para general videos:
calidad 360p el costo es de 0.45, y el costo de 1200 créditos en pixverse es de 10 USD, por lo tanto, si sacamos la cuenta cuantos videos podemos hacer con la API de comfyUI a una calidad mínima con 10 USD:
en total con 10 dólares podemos hacer 22 videos.
y en el plan minimo vamos a poder hacer 60 videos en la calidad mas baja

Resolución | Pixverse (Créditos) | Costo USD (Plataforma) | API ComfyUI (USD) | Margen de costo por video (%) | ¿Más barato?
-----------|---------------------|------------------------|-------------------|-------------------------------|---------------
360p       | 20 créditos         | $0.17                  | $0.45             | +164.7%                       | Plataforma
540p       | 30 créditos         | $0.25                  | $0.45             | +80.0%                        | Plataforma
720p       | 40 créditos         | $0.33                  | $0.60             | +81.8%                        | Plataforma
1080p      | 80 créditos         | $0.67                  | $1.20             | +79.1%                        | Plataforma


📌 Cómo se calcula el margen de costo por video:
Margen (%) = [(Precio API - Precio Plataforma) / Precio Plataforma] × 100 

Ejemplo para 360p:
→ ($0.45 - $0.17) / $0.17 = 1.647 → +164.7% más caro usar la API

💡 Interpretación:
Usar la API de ComfyUI casi triplica el costo en 360p frente a usar créditos directos.
En resoluciones más altas, el margen se mantiene alto: ~80% más caro en promedio.
Esto es crítico si generas muchos videos: el ahorro escala rápido.


1. Clone the repository:
```bash
cd custom_nodes/
git clone https://github.com/systemaiofinterest-wq/ComfyUI-Pixverse-AI-V2.git
cd ComfyUI-Pixverse-AI-V2
pip install -r requirements.txt
```
