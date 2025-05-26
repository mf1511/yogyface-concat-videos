#!/usr/bin/env python3
"""
Script pour télécharger et concaténer des vidéos
Refactored for web API usage with compression support
"""

import os
import sys
import subprocess
import tempfile
import argparse
from urllib.parse import urlparse
import requests
from pathlib import Path
import time
import shutil

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

def get_file_size_mb(file_path):
    """Retourne la taille du fichier en MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    except OSError:
        return 0

def compress_video(input_path, target_size_mb=100, max_attempts=4):
    """
    Compresse une vidéo en utilisant une approche itérative pour atteindre la taille cible
    tout en préservant la meilleure qualité possible
    """
    print(f"🎬 Démarrage compression: {os.path.basename(input_path)}")
    
    # Vérification des outils
    if not check_ffmpeg_available():
        print("❌ ffmpeg/ffprobe non disponible")
        return False
    
    # Taille originale
    original_size = os.path.getsize(input_path)
    original_mb = original_size / (1024 * 1024)
    print(f"📊 Taille originale: {original_mb:.1f} MB")
    
    if original_mb <= target_size_mb:
        print(f"✅ Fichier déjà sous {target_size_mb}MB")
        return True
    
    # Obtenir la durée de la vidéo
    duration = get_video_duration(input_path)
    if not duration:
        print("❌ Impossible d'obtenir la durée de la vidéo")
        return False
    
    print(f"⏱️  Durée: {duration:.1f} secondes")
    
    # Paramètres de compression progressive
    compression_attempts = [
        {"crf": 23, "preset": "medium", "name": "Qualité élevée"},
        {"crf": 25, "preset": "medium", "name": "Qualité moyenne-élevée"},
        {"crf": 27, "preset": "fast", "name": "Qualité moyenne"},
        {"crf": 30, "preset": "fast", "name": "Qualité acceptable"}
    ]
    
    temp_output = None
    
    try:
        for attempt, params in enumerate(compression_attempts, 1):
            print(f"\n🔄 Tentative {attempt}/{len(compression_attempts)}: {params['name']}")
            
            # Calcul du bitrate cible pour cette tentative
            target_size_bits = target_size_mb * 8 * 1024 * 1024
            # Réduction progressive: 95%, 90%, 85%, 80% de la taille cible
            size_factor = 1.0 - (attempt * 0.05)
            adjusted_target_bits = target_size_bits * size_factor
            target_bitrate = int((adjusted_target_bits / duration) * 0.85)  # 85% pour vidéo, 15% pour audio
            
            print(f"🎯 Bitrate cible: {target_bitrate} bps (CRF: {params['crf']})")
            
            # Fichier temporaire pour cette tentative
            temp_output = tempfile.mktemp(suffix='_compressed.mp4')
            
            # Commande ffmpeg optimisée
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',
                '-preset', params['preset'],
                '-crf', str(params['crf']),
                '-b:v', str(target_bitrate),
                '-maxrate', str(int(target_bitrate * 1.2)),
                '-bufsize', str(int(target_bitrate * 2)),
                '-c:a', 'aac',
                '-b:a', '96k',  # Audio de meilleure qualité
                '-threads', '0',
                '-movflags', '+faststart',  # Optimisation pour streaming
                '-y', temp_output
            ]
            
            # Exécution avec timeout
            print(f"⚙️  Compression en cours...")
            start_time = time.time()
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                elapsed = time.time() - start_time
                
                if result.returncode != 0:
                    print(f"❌ Erreur ffmpeg: {result.stderr}")
                    continue
                
                # Vérifier la taille du résultat
                if os.path.exists(temp_output):
                    compressed_size = os.path.getsize(temp_output)
                    compressed_mb = compressed_size / (1024 * 1024)
                    
                    print(f"📏 Résultat: {compressed_mb:.1f} MB (temps: {elapsed:.1f}s)")
                    
                    # Succès si on est dans la plage acceptable
                    if compressed_mb <= target_size_mb:
                        # Remplacer le fichier original
                        shutil.move(temp_output, input_path)
                        
                        ratio = compressed_size / original_size
                        print(f"✅ Compression réussie!")
                        print(f"📊 Taille finale: {compressed_mb:.1f} MB")
                        print(f"📉 Réduction: {((1-ratio)*100):.1f}%")
                        print(f"🎯 Qualité: {params['name']}")
                        
                        return True
                    else:
                        print(f"⚠️  Encore trop gros ({compressed_mb:.1f} MB > {target_size_mb} MB)")
                        # Nettoyer le fichier temporaire
                        if os.path.exists(temp_output):
                            os.unlink(temp_output)
                else:
                    print("❌ Fichier de sortie non créé")
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout après 5 minutes")
                continue
            except Exception as e:
                print(f"❌ Erreur: {e}")
                continue
        
        # Si toutes les tentatives ont échoué
        print(f"❌ Impossible de compresser sous {target_size_mb}MB après {len(compression_attempts)} tentatives")
        return False
        
    finally:
        # Nettoyer les fichiers temporaires
        if temp_output and os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except:
                pass

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

def check_ffmpeg():
    """Vérifie que ffmpeg est installé"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_ffmpeg_available():
    """Vérifie si ffmpeg et ffprobe sont disponibles"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_duration(video_path):
    """Obtient la durée de la vidéo en secondes"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        
        if duration_str:
            return float(duration_str)
    except (subprocess.CalledProcessError, ValueError):
        pass
    return None

def process_videos_from_urls(urls, output_path, keep_temp=False, max_size_mb=100):
    """
    Process videos from URLs - main logic extracted for API usage
    Returns (success: bool, error_message: str)
    """
    if not check_ffmpeg():
        return False, "ffmpeg n'est pas installé ou accessible"
    
    # Crée un dossier temporaire pour les téléchargements
    temp_dir = tempfile.mkdtemp(prefix='video_concat_')
    downloaded_videos = []
    
    try:
        # Télécharge chaque vidéo
        for i, url in enumerate(urls):
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
                    return False, f"Le fichier {url} ne semble pas être une vidéo valide"
            else:
                return False, f"Impossible de télécharger {url}"
        
        if not downloaded_videos:
            return False, "Aucune vidéo n'a pu être téléchargée"
        
        # Vérifie la taille finale et compresse si nécessaire
        if len(downloaded_videos) > 1:
            if concatenate_videos(downloaded_videos, output_path):
                file_size = get_file_size_mb(output_path)
                print(f"✓ Vidéo concaténée: {file_size:.1f}MB")
                
                # Compression si nécessaire
                if file_size > max_size_mb:
                    print(f"⚠ Fichier trop volumineux ({file_size:.1f}MB), compression en cours...")
                    
                    if compress_video(output_path, max_size_mb):
                        file_size = get_file_size_mb(output_path)  # Update file size after compression
                        print(f"✓ Vidéo compressée avec succès: {file_size:.1f}MB")
                    else:
                        print(f"⚠ Compression échouée, fichier reste à {file_size:.1f}MB")
            else:
                print("✗ Erreur lors de la concaténation")
                return None, []
        else:
            # Un seul fichier, copie directement
            print("⚠ Une seule vidéo téléchargée, copie vers la sortie...")
            import shutil
            shutil.copy2(downloaded_videos[0], output_path)
            file_size = get_file_size_mb(output_path)
            print(f"✓ Fichier copié: {file_size:.1f}MB")
            
            # Compression si nécessaire
            if file_size > max_size_mb:
                print(f"⚠ Fichier unique trop volumineux ({file_size:.1f}MB), compression...")
                if compress_video(output_path, max_size_mb):
                    file_size = get_file_size_mb(output_path)  # Update file size after compression
                    print(f"✓ Fichier unique compressé: {file_size:.1f}MB")
        
        return True, f"Vidéo créée avec succès ({file_size:.1f}MB)"
        
    finally:
        # Nettoie les fichiers temporaires
        if not keep_temp:
            import shutil
            shutil.rmtree(temp_dir)

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Télécharge et concatène des vidéos')
    parser.add_argument('urls', nargs='+', help='URLs des vidéos à télécharger')
    parser.add_argument('-o', '--output', default='video_finale.mp4', 
                       help='Nom du fichier de sortie (défaut: video_finale.mp4)')
    parser.add_argument('--keep-temp', action='store_true', 
                       help='Garde les fichiers temporaires téléchargés')
    parser.add_argument('--max-size', type=int, default=100,
                       help='Taille maximale en MB avant compression (défaut: 100)')
    
    args = parser.parse_args()
    
    success, message = process_videos_from_urls(args.urls, args.output, args.keep_temp, args.max_size)
    
    if success:
        print(f"🎉 Terminé! Vidéo finale: {args.output}")
        print(f"📊 {message}")
    else:
        print(f"✗ Erreur: {message}")
        sys.exit(1)

if __name__ == "__main__":
    main() 