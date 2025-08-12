"""
Google Drive Integration Utils for CAT Preparation Platform
Handles fetching images from Google Drive share links for bulk question upload
"""

import re
import requests
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class GoogleDriveImageFetcher:
    """Utility class for fetching images from Google Drive share links"""
    
    @staticmethod
    def extract_file_id_from_url(google_drive_url: str) -> Optional[str]:
        """
        Extract Google Drive file ID from various Google Drive URL formats
        
        Supported formats:
        - https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing
        - https://drive.google.com/open?id={FILE_ID}
        - https://drive.google.com/file/d/{FILE_ID}/view
        - https://docs.google.com/document/d/{FILE_ID}/edit
        """
        if not google_drive_url or not isinstance(google_drive_url, str):
            return None
            
        # Pattern 1: /file/d/{FILE_ID}/view or /file/d/{FILE_ID}/edit
        pattern1 = r'/file/d/([a-zA-Z0-9-_]+)/'
        match1 = re.search(pattern1, google_drive_url)
        if match1:
            return match1.group(1)
            
        # Pattern 2: ?id={FILE_ID} or &id={FILE_ID}
        pattern2 = r'[?&]id=([a-zA-Z0-9-_]+)'
        match2 = re.search(pattern2, google_drive_url)
        if match2:
            return match2.group(1)
            
        # Pattern 3: /d/{FILE_ID}/edit (for docs/sheets/slides)
        pattern3 = r'/d/([a-zA-Z0-9-_]+)/'
        match3 = re.search(pattern3, google_drive_url)
        if match3:
            return match3.group(1)
            
        logger.warning(f"Could not extract file ID from Google Drive URL: {google_drive_url}")
        return None
    
    @staticmethod
    def get_direct_download_url(file_id: str) -> str:
        """
        Convert Google Drive file ID to direct download URL
        """
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    @staticmethod
    def fetch_image_from_google_drive(
        google_drive_url: str,
        upload_dir: Path,
        alt_text: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Fetch image from Google Drive URL and save locally
        
        Returns:
            Tuple[success: bool, local_image_url: str, error_message: str]
        """
        try:
            # Extract file ID from URL
            file_id = GoogleDriveImageFetcher.extract_file_id_from_url(google_drive_url)
            if not file_id:
                return False, None, "Could not extract file ID from Google Drive URL"
            
            # Get direct download URL
            download_url = GoogleDriveImageFetcher.get_direct_download_url(file_id)
            
            # Download the image
            logger.info(f"Fetching image from Google Drive: {download_url}")
            
            # Set headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(download_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually an image
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                # Try to detect from content
                content_start = response.content[:10]
                if not (content_start.startswith(b'\x89PNG') or  # PNG
                       content_start.startswith(b'\xff\xd8\xff') or  # JPEG
                       content_start.startswith(b'GIF8') or  # GIF
                       content_start.startswith(b'BM')):  # BMP
                    return False, None, f"Downloaded content is not a valid image (Content-Type: {content_type})"
            
            # Determine file extension from content type or URL
            extension = '.jpg'  # Default
            if 'png' in content_type:
                extension = '.png'
            elif 'gif' in content_type:
                extension = '.gif'
            elif 'bmp' in content_type:
                extension = '.bmp'
            elif 'webp' in content_type:
                extension = '.webp'
            
            # Generate unique filename
            file_uuid = str(uuid.uuid4())
            filename = f"gdrive_{file_uuid}{extension}"
            file_path = upload_dir / filename
            
            # Ensure upload directory exists
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the image
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Generate local URL
            local_image_url = f"/uploads/images/{filename}"
            
            logger.info(f"Successfully fetched and saved image: {filename} ({len(response.content)} bytes)")
            
            return True, local_image_url, None
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout while downloading image from Google Drive"
            logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error downloading image from Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error fetching image from Google Drive: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    @staticmethod
    def validate_google_drive_url(url: str) -> bool:
        """
        Validate if the URL is a valid Google Drive share link
        """
        if not url or not isinstance(url, str):
            return False
            
        # Check if it's a Google Drive domain
        google_domains = [
            'drive.google.com',
            'docs.google.com',
            'sheets.google.com',
            'slides.google.com'
        ]
        
        return any(domain in url.lower() for domain in google_domains)
    
    @staticmethod
    def process_csv_image_urls(csv_data: list, upload_dir: Path) -> list:
        """
        Process CSV data and fetch images from Google Drive URLs
        
        Args:
            csv_data: List of dictionaries containing question data
            upload_dir: Directory to save downloaded images
            
        Returns:
            Updated CSV data with local image URLs
        """
        processed_data = []
        
        for i, row in enumerate(csv_data):
            try:
                # Check if row has image_url with Google Drive link
                image_url = row.get('image_url', '').strip()
                
                if image_url and GoogleDriveImageFetcher.validate_google_drive_url(image_url):
                    logger.info(f"Processing Google Drive image for row {i+1}: {image_url}")
                    
                    # Fetch image from Google Drive
                    alt_text = row.get('image_alt_text', '').strip()
                    success, local_url, error = GoogleDriveImageFetcher.fetch_image_from_google_drive(
                        image_url, upload_dir, alt_text
                    )
                    
                    if success:
                        # Update row with local image URL
                        row['image_url'] = local_url
                        row['has_image'] = True
                        if not row.get('image_alt_text'):
                            row['image_alt_text'] = f"Question image {i+1}"
                        
                        logger.info(f"Successfully processed image for row {i+1}")
                    else:
                        # Log error but continue processing
                        logger.error(f"Failed to fetch image for row {i+1}: {error}")
                        row['has_image'] = False
                        row['image_url'] = None
                        row['image_alt_text'] = f"Image could not be loaded: {error}"
                        
                elif image_url:
                    # Non-Google Drive URL - log warning
                    logger.warning(f"Row {i+1} has non-Google Drive image URL: {image_url}")
                    row['has_image'] = False
                    row['image_url'] = None
                    
                else:
                    # No image URL - set defaults
                    row['has_image'] = False
                    row['image_url'] = None
                    
                processed_data.append(row)
                
            except Exception as e:
                logger.error(f"Error processing row {i+1}: {str(e)}")
                # Continue with row as-is
                row['has_image'] = False
                row['image_url'] = None
                processed_data.append(row)
        
        return processed_data