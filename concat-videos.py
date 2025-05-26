#!/usr/bin/env python3
"""
Script pour télécharger et concaténer des vidéos
"""

import os
import sys
import subprocess
import tempfile
import argparse
from urllib.parse import urlparse
import requests
from pathlib import Path

def download_video(url, output_path):
    """Télécharge une vidéo depuis une URL"""
    try:
        print(f"Téléchargement de {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ Téléchargé: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Erreur lors du téléchargement de {url}: {e}")
        return False

def get_video_info(video_path):
    """Récupère les informations d'une vidéo avec ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def concatenate_videos(video_paths, output_path):
    """Concatène plusieurs vidéos avec ffmpeg"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        for video_path in video_paths:
            # Échappe les caractères spéciaux pour ffmpeg
            escaped_path = video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    try:
        print("Concaténation des vidéos...")
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file,
            '-c', 'copy', '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Vidéo finale créée: {output_path}")
            return True
        else:
            print(f"✗ Erreur ffmpeg: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Erreur lors de la concaténation: {e}")
        return False
    finally:
        # Nettoie le fichier temporaire
        os.unlink(concat_file)

def main():
    parser = argparse.ArgumentParser(description='Télécharge et concatène des vidéos')
    parser.add_argument('urls', nargs='+', help='URLs des vidéos à télécharger')
    parser.add_argument('-o', '--output', default='video_finale.mp4', 
                       help='Nom du fichier de sortie (défaut: video_finale.mp4)')
    parser.add_argument('--keep-temp', action='store_true', 
                       help='Garde les fichiers temporaires téléchargés')
    
    args = parser.parse_args()
    
    # Vérifie que ffmpeg est installé
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Erreur: ffmpeg n'est pas installé ou accessible")
        print("Installez ffmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    # Crée un dossier temporaire pour les téléchargements
    temp_dir = tempfile.mkdtemp(prefix='video_concat_')
    downloaded_videos = []
    
    try:
        # Télécharge chaque vidéo
        for i, url in enumerate(args.urls):
            # Génère un nom de fichier temporaire
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or f"video_{i+1}.mp4"
            
            # Assure-toi que le fichier a une extension vidéo
            if not any(filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']):
                filename += '.mp4'
            
            temp_path = os.path.join(temp_dir, filename)
            
            if download_video(url, temp_path):
                # Vérifie que le fichier est une vidéo valide
                if get_video_info(temp_path):
                    downloaded_videos.append(temp_path)
                else:
                    print(f"⚠ Le fichier {temp_path} ne semble pas être une vidéo valide")
            else:
                print(f"⚠ Impossible de télécharger {url}")
        
        if not downloaded_videos:
            print("✗ Aucune vidéo n'a pu être téléchargée")
            sys.exit(1)
        
        if len(downloaded_videos) < 2:
            print("⚠ Une seule vidéo téléchargée, copie vers la sortie...")
            import shutil
            shutil.copy2(downloaded_videos[0], args.output)
        else:
            # Concatène les vidéos
            if not concatenate_videos(downloaded_videos, args.output):
                sys.exit(1)
        
        print(f"🎉 Terminé! Vidéo finale: {args.output}")
        
    finally:
        # Nettoie les fichiers temporaires
        if not args.keep_temp:
            import shutil
            shutil.rmtree(temp_dir)
        else:
            print(f"Fichiers temporaires conservés dans: {temp_dir}")

if __name__ == "__main__":
    main()