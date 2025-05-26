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

def compress_video(input_path, output_path, target_size_mb=100):
    """
    Compresse une vidéo pour qu'elle fasse moins de target_size_mb MB
    Uses iterative compression to ensure target is met
    """
    try:
        print(f"Compression de la vidéo (cible: {target_size_mb}MB)...")
        
        # Get video duration for bitrate calculation
        duration_cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', input_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
        duration = float(duration_result.stdout.strip())
        
        # More aggressive initial calculation (85% of target to ensure we stay under)
        target_size_mb_adjusted = target_size_mb * 0.85
        
        # Calculate target bitrate (in kbps) for adjusted target file size
        target_video_bitrate = int((target_size_mb_adjusted * 8 * 1024) / duration * 0.85)
        target_audio_bitrate = min(96, int((target_size_mb_adjusted * 8 * 1024) / duration * 0.15))
        
        # Ensure minimum quality but be more aggressive
        target_video_bitrate = max(target_video_bitrate, 300)  # Lower minimum for aggressive compression
        target_audio_bitrate = max(target_audio_bitrate, 48)   # Lower audio quality if needed
        
        print(f"Bitrates calculés - Vidéo: {target_video_bitrate}kbps, Audio: {target_audio_bitrate}kbps")
        
        # More aggressive compression settings
        crf_value = 28  # Higher CRF = more compression (was 23)
        
        # Try up to 3 compression attempts with increasing aggressiveness
        for attempt in range(3):
            if attempt > 0:
                print(f"Tentative {attempt + 1}/3 avec compression plus agressive...")
                # Increase compression for retry attempts
                crf_value = min(32, crf_value + 3)  # Cap at CRF 32
                target_video_bitrate = int(target_video_bitrate * 0.8)  # Reduce bitrate by 20%
                target_audio_bitrate = max(32, int(target_audio_bitrate * 0.8))  # Minimum 32kbps audio
                print(f"Nouveau CRF: {crf_value}, Bitrates: {target_video_bitrate}kbps / {target_audio_bitrate}kbps")
            
            # Compression command with aggressive settings
            temp_output = output_path + f'.temp{attempt}.mp4'
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',           # H.264 codec for good compression
                '-preset', 'medium',          # Balance between speed and compression
                '-crf', str(crf_value),      # Quality setting (higher = more compression)
                '-b:v', f'{target_video_bitrate}k',  # Target video bitrate
                '-maxrate', f'{int(target_video_bitrate * 1.1)}k',  # Tighter max bitrate
                '-bufsize', f'{target_video_bitrate}k',    # Smaller buffer size
                '-c:a', 'aac',               # AAC audio codec
                '-b:a', f'{target_audio_bitrate}k',  # Audio bitrate
                '-movflags', '+faststart',    # Optimize for web streaming
                '-y', temp_output
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                compressed_size = get_file_size_mb(temp_output)
                print(f"Tentative {attempt + 1}: {compressed_size:.1f}MB")
                
                # Check if we achieved the target
                if compressed_size <= target_size_mb:
                    # Success! Move temp file to final output
                    os.replace(temp_output, output_path)
                    print(f"✓ Vidéo compressée avec succès: {compressed_size:.1f}MB (cible: {target_size_mb}MB)")
                    
                    # Clean up any other temp files
                    for i in range(attempt + 1, 3):
                        temp_file = output_path + f'.temp{i}.mp4'
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    
                    return True
                else:
                    # Continue to next attempt if we have tries left
                    if attempt < 2:
                        print(f"⚠ Encore trop volumineux ({compressed_size:.1f}MB > {target_size_mb}MB), nouvelle tentative...")
                        # Keep this temp file as input for next attempt
                        input_path = temp_output
                    else:
                        # Last attempt failed, but still better than original
                        print(f"⚠ Impossible d'atteindre {target_size_mb}MB après 3 tentatives")
                        print(f"Meilleur résultat: {compressed_size:.1f}MB")
                        os.replace(temp_output, output_path)
                        return True
            else:
                print(f"✗ Erreur de compression (tentative {attempt + 1}): {result.stderr}")
                # Clean up failed temp file
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                
                if attempt == 2:  # Last attempt
                    return False
        
        return False
            
    except Exception as e:
        print(f"✗ Erreur lors de la compression: {e}")
        return False

def concatenate_videos(video_paths, output_path, max_size_mb=100):
    """Concatène plusieurs vidéos avec ffmpeg et compression si nécessaire"""
    
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
            file_size = get_file_size_mb(output_path)
            print(f"✓ Vidéo finale créée: {output_path} ({file_size:.1f}MB)")
            
            # Check if compression is needed
            if file_size > max_size_mb:
                print(f"⚠ Fichier trop volumineux ({file_size:.1f}MB > {max_size_mb}MB), compression en cours...")
                
                # Create compressed version
                temp_compressed = output_path + '.compressed.mp4'
                
                if compress_video(output_path, temp_compressed, max_size_mb):
                    # Replace original with compressed version
                    os.replace(temp_compressed, output_path)
                    final_size = get_file_size_mb(output_path)
                    print(f"✓ Vidéo compressée avec succès: {final_size:.1f}MB")
                else:
                    print("⚠ Compression échouée, conservation du fichier original")
                    # Clean up failed compression file
                    if os.path.exists(temp_compressed):
                        os.remove(temp_compressed)
            
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
        
        if len(downloaded_videos) < 2:
            print("⚠ Une seule vidéo téléchargée, copie vers la sortie...")
            import shutil
            shutil.copy2(downloaded_videos[0], output_path)
            
            # Check if single video needs compression
            file_size = get_file_size_mb(output_path)
            if file_size > max_size_mb:
                print(f"⚠ Fichier unique trop volumineux ({file_size:.1f}MB), compression...")
                temp_compressed = output_path + '.compressed.mp4'
                if compress_video(output_path, temp_compressed, max_size_mb):
                    os.replace(temp_compressed, output_path)
                    print(f"✓ Fichier unique compressé: {get_file_size_mb(output_path):.1f}MB")
        else:
            # Concatène les vidéos (avec compression automatique si nécessaire)
            if not concatenate_videos(downloaded_videos, output_path, max_size_mb):
                return False, "Erreur lors de la concaténation"
        
        final_size = get_file_size_mb(output_path)
        return True, f"Vidéo créée avec succès ({final_size:.1f}MB)"
        
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