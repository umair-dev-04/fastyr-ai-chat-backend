import os
import uuid
import aiofiles
from typing import Optional
from fastapi import UploadFile, HTTPException, status, Request
from PIL import Image
import io
from datetime import datetime

class FileUploadManager:
    def __init__(self):
        self.upload_dir = "uploads"
        self.avatar_dir = os.path.join(self.upload_dir, "avatars")
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.max_dimensions = (800, 800)  # Max width/height
        
        # Create upload directories if they don't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.avatar_dir, exist_ok=True)
    
    def validate_file_type(self, file: UploadFile) -> bool:
        """Validate if the uploaded file is an image based on extension"""
        if not file.filename:
            return False
        
        # Check file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        return file_extension in self.allowed_extensions
    
    def validate_file_size(self, file_content: bytes) -> bool:
        """Validate file size"""
        return len(file_content) <= self.max_file_size
    
    async def validate_image_content(self, file_content: bytes) -> bool:
        """Validate image content by trying to open it with PIL"""
        try:
            # Try to open the image with PIL to validate it's a real image
            image = Image.open(io.BytesIO(file_content))
            image.verify()  # Verify the image
            return True
        except Exception:
            return False
    
    async def process_image(self, file_content: bytes, file_extension: str) -> bytes:
        """Process and optimize the image"""
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(file_content))
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Resize if image is too large
            if image.width > self.max_dimensions[0] or image.height > self.max_dimensions[1]:
                image.thumbnail(self.max_dimensions, Image.Resampling.LANCZOS)
            
            # Determine output format based on original extension
            if file_extension.lower() in ['.jpg', '.jpeg']:
                output_format = 'JPEG'
                save_kwargs = {'quality': 85, 'optimize': True}
            elif file_extension.lower() == '.png':
                output_format = 'PNG'
                save_kwargs = {'optimize': True}
            elif file_extension.lower() == '.gif':
                output_format = 'GIF'
                save_kwargs = {}
            elif file_extension.lower() == '.webp':
                output_format = 'WEBP'
                save_kwargs = {'quality': 85}
            else:
                # Default to JPEG
                output_format = 'JPEG'
                save_kwargs = {'quality': 85, 'optimize': True}
            
            # Save optimized image
            output = io.BytesIO()
            image.save(output, format=output_format, **save_kwargs)
            output.seek(0)
            
            return output.getvalue()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process image: {str(e)}"
            )
    
    def generate_filename(self, original_filename: str) -> str:
        """Generate unique filename for uploaded file"""
        # Get file extension
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"avatar_{timestamp}_{unique_id}{file_extension}"
    
    async def save_avatar(self, file: UploadFile, user_id: int) -> str:
        """Save avatar file and return the relative file path"""
        # Validate file type
        if not self.validate_file_type(file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPG, PNG, GIF, and WebP images are allowed."
            )
        
        # Read file content
        try:
            file_content = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {str(e)}"
            )
        
        # Validate file size
        if not self.validate_file_size(file_content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {self.max_file_size // (1024*1024)}MB."
            )
        
        # Validate image content by trying to open it
        if not await self.validate_image_content(file_content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file. Please upload a valid image."
            )
        
        # Get file extension for processing
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Process and optimize image
        processed_content = await self.process_image(file_content, file_extension)
        
        # Generate filename
        filename = self.generate_filename(file.filename)
        file_path = os.path.join(self.avatar_dir, filename)
        
        # Save file
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(processed_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Return relative path for database storage (always relative)
        return f"/uploads/avatars/{filename}"
    
    def get_avatar_url(self, relative_path: str, request: Request) -> str:
        """Convert relative path to full URL using request's base URL"""
        if relative_path and relative_path.startswith('/uploads/'):
            # Use the request's base URL to construct the full URL
            base_url = str(request.base_url).rstrip('/')
            return f"{base_url}{relative_path}"
        return relative_path
    
    def delete_avatar(self, relative_path: str) -> bool:
        """Delete avatar file from storage"""
        try:
            if relative_path and relative_path.startswith('/uploads/'):
                # Convert relative path to file system path
                file_system_path = relative_path.replace('/uploads/', 'uploads/')
                if os.path.exists(file_system_path):
                    os.remove(file_system_path)
                    return True
            return False
        except Exception:
            return False

# Initialize global file upload manager
file_upload_manager = FileUploadManager() 