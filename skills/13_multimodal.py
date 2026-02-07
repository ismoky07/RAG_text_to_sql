"""
Skill 13 : Multimodal I/O (Entrées/Sorties Multimodales)
===========================================================
Concept Agno : Les agents peuvent traiter et générer du contenu multimodal :
images, audio, vidéo et fichiers (PDF, documents).

4 classes média : Image, Audio, Video, File

Documentation : https://docs.agno.com/input-output/multimodal
"""

from agno.agent import Agent
from agno.media import Audio, File, Image, Video
from agno.models.openai import OpenAIChat


# ── 1. Agent avec entrée image ───────────────────────────────────────────────
agent_vision = Agent(
    model=OpenAIChat(id="gpt-4o"),  # Modèle avec capacité vision
    instructions="Tu analyses les images fournies. "
                 "Décris ce que tu vois en détail. "
                 "Réponds en français.",
    markdown=True,
)


def analyze_image_from_url(url: str, question: str = "Que vois-tu dans cette image ?"):
    """Analyser une image depuis une URL."""
    response = agent_vision.run(
        question,
        images=[Image(url=url)],
    )
    return response.content


def analyze_image_from_file(filepath: str, question: str = "Décris cette image."):
    """Analyser une image depuis un fichier local."""
    response = agent_vision.run(
        question,
        images=[Image(filepath=filepath)],
    )
    return response.content


def compare_images(url1: str, url2: str):
    """Comparer deux images."""
    response = agent_vision.run(
        "Compare ces deux images. Quelles sont les différences ?",
        images=[Image(url=url1), Image(url=url2)],
    )
    return response.content


# ── 2. Agent avec entrée audio ───────────────────────────────────────────────
# Nécessite un modèle compatible audio (ex: gpt-4o-audio-preview)
#
# agent_audio = Agent(
#     model=OpenAIChat(
#         id="gpt-4o-audio-preview",
#         modalities=["text"],
#     ),
#     instructions="Tu transcris et analyses les fichiers audio. "
#                  "Réponds en français.",
# )
#
# def transcribe_audio(filepath: str):
#     """Transcrire un fichier audio."""
#     response = agent_audio.run(
#         "Transcris et résume cet audio.",
#         audio=[Audio(filepath=filepath)],
#     )
#     return response.content


# ── 3. Agent avec entrée fichier (PDF, documents) ────────────────────────────
# from agno.models.anthropic import Claude
#
# agent_document = Agent(
#     model=Claude(id="claude-sonnet-4-5"),
#     instructions="Tu analyses les documents fournis. "
#                  "Extrais les informations clés. "
#                  "Réponds en français.",
# )
#
# def analyze_pdf(filepath: str, question: str = "Résume ce document."):
#     """Analyser un fichier PDF."""
#     response = agent_document.run(
#         question,
#         files=[File(filepath=filepath)],
#     )
#     return response.content


# ── 4. Agent avec sortie image (génération) ──────────────────────────────────
# from agno.tools.dalle import DalleTools
#
# agent_image_gen = Agent(
#     model=OpenAIChat(id="gpt-4o"),
#     tools=[DalleTools()],
#     instructions="Tu génères des images à partir de descriptions.",
# )
#
# def generate_image(prompt: str):
#     """Générer une image à partir d'un prompt."""
#     agent_image_gen.run(f"Génère une image : {prompt}")
#     images = agent_image_gen.get_images()
#     for img in images:
#         print(f"Image générée : {img.url}")
#     return images


# ── 5. Agent avec sortie audio ───────────────────────────────────────────────
# from agno.utils.audio import write_audio_to_file
#
# agent_tts = Agent(
#     model=OpenAIChat(
#         id="gpt-4o-audio-preview",
#         modalities=["text", "audio"],
#         audio={"voice": "alloy", "format": "wav"},
#     ),
# )
#
# def text_to_speech(text: str, output_path: str = "output.wav"):
#     """Convertir du texte en audio."""
#     response = agent_tts.run(text)
#     if response.response_audio:
#         write_audio_to_file(response.response_audio.content, output_path)
#         print(f"Audio sauvegardé : {output_path}")


# ── 6. Entrée vidéo (Gemini uniquement) ──────────────────────────────────────
# from agno.models.google import Gemini
#
# agent_video = Agent(
#     model=Gemini(id="gemini-2.0-flash-exp"),
#     instructions="Tu analyses les vidéos. Décris ce qui se passe.",
# )
#
# def analyze_video(filepath: str):
#     """Analyser une vidéo (Gemini uniquement)."""
#     response = agent_video.run(
#         "Décris ce qui se passe dans cette vidéo.",
#         videos=[Video(filepath=filepath)],
#     )
#     return response.content


# ── 7. Exécution ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Skill 13 : Multimodal I/O")
    print("=" * 60)
    print()
    print("Types d'entrée supportés :")
    print("  - Image : URL, filepath, bytes")
    print("  - Audio : URL, filepath, bytes (+ format)")
    print("  - Video : URL, filepath (Gemini uniquement)")
    print("  - File  : URL, filepath (PDF, documents)")
    print()
    print("Types de sortie supportés :")
    print("  - Image : via DalleTools")
    print("  - Audio : via modèles audio (gpt-4o-audio-preview)")
    print()
    print("Pour exécuter : décommentez le code selon votre cas d'usage.")
