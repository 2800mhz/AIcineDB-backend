"""
AI-Powered Banner Generator using HuggingFace Hub InferenceClient
Inspired by YouTube Music's AI Playlist Photo feature
"""
import os
import logging
from typing import List, Dict, Optional
from io import BytesIO
from PIL import Image
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

class AIBannerGenerator:
    """Generate custom banners using HuggingFace InferenceClient"""
    
    # Available AI models with providers
    MODELS = {
        "z-image-turbo": {
            "name": "Z-Image Turbo (Fast)",
            "model": "Tongyi-MAI/Z-Image-Turbo",
            "provider": "fal-ai",
            "reliable": True,
            "speed": "fast"
        },
        "qwen-image": {
            "name": "Qwen Image (Quality)",
            "model": "Qwen/Qwen-Image",
            "provider": "fal-ai",
            "reliable": True,
            "speed": "medium"
        },
        "sdxl": {
            "name": "Stable Diffusion XL",
            "model": "stabilityai/stable-diffusion-xl-base-1.0",
            "provider": "nscale",
            "reliable": True,
            "speed": "medium"
        }
    }
    
    # Category templates
    CATEGORIES = {
        "cinematic": {
            "name": "Cinematic",
            "icon": "🎬",
            "base_prompt": "cinematic film scene"
        },
        "landscape": {
            "name": "Landscape",
            "icon": "🏔️",
            "base_prompt": "beautiful landscape"
        },
        "space": {
            "name": "Space",
            "icon": "🌌",
            "base_prompt": "cosmic space scene"
        },
        "abstract": {
            "name": "Abstract",
            "icon": "🎨",
            "base_prompt": "abstract art"
        },
        "vintage": {
            "name": "Vintage Film",
            "icon": "📽️",
            "base_prompt": "vintage film aesthetic"
        },
        "noir": {
            "name": "Film Noir",
            "icon": "🕵️",
            "base_prompt": "film noir style"
        }
    }
    
    # Style modifiers
    STYLES = [
        {"id": "oil-painting", "name": "Oil Painting", "prompt": "oil painting style"},
        {"id": "surrealist", "name": "Surrealist", "prompt": "surrealist art"},
        {"id": "retro", "name": "Retro", "prompt": "retro 80s aesthetic"},
        {"id": "minimalist", "name": "Minimalist", "prompt": "minimalist design"},
        {"id": "dramatic", "name": "Dramatic", "prompt": "dramatic lighting"},
        {"id": "pastel", "name": "Pastel", "prompt": "soft pastel colors"},
    ]
    
    # Content elements
    CINEMA_ELEMENTS = [
        {"id": "camera", "name": "Camera", "prompt": "vintage film camera"},
        {"id": "projector", "name": "Projector", "prompt": "film projector"},
        {"id": "reel", "name": "Film Reel", "prompt": "film reel and tape"},
        {"id": "clapperboard", "name": "Clapperboard", "prompt": "movie clapperboard"},
        {"id": "theater", "name": "Theater", "prompt": "classic movie theater"},
        {"id": "spotlight", "name": "Spotlight", "prompt": "dramatic spotlight"},
    ]
    
    # Color palettes
    COLOR_PALETTES = [
        {"id": "warm", "name": "Warm", "prompt": "warm color palette, golden hour"},
        {"id": "cool", "name": "Cool", "prompt": "cool blue tones, twilight"},
        {"id": "vibrant", "name": "Vibrant", "prompt": "vibrant saturated colors"},
        {"id": "monochrome", "name": "Monochrome", "prompt": "black and white, high contrast"},
        {"id": "neon", "name": "Neon", "prompt": "neon colors, cyberpunk vibes"},
    ]
    
    def __init__(self):
        self.hf_token = os.getenv('HUGGING_FACE_TOKEN')
        
        if not self.hf_token:
            logger.warning("⚠️ HUGGING_FACE_TOKEN not set - AI banner generation disabled")
    
    def build_prompt(
        self,
        category: str,
        style: str,
        element: Optional[str] = None,
        color_palette: str = "vibrant"
    ) -> str:
        """Build complete prompt from user selections"""
        
        # Base from category
        prompt_parts = [self.CATEGORIES[category]["base_prompt"]]
        
        # Add style
        style_obj = next((s for s in self.STYLES if s["id"] == style), None)
        if style_obj:
            prompt_parts.append(style_obj["prompt"])
        
        # Add cinema element
        if element:
            element_obj = next((e for e in self.CINEMA_ELEMENTS if e["id"] == element), None)
            if element_obj:
                prompt_parts.append(f"featuring {element_obj['prompt']}")
        
        # Add color palette
        palette_obj = next((p for p in self.COLOR_PALETTES if p["id"] == color_palette), None)
        if palette_obj:
            prompt_parts.append(palette_obj["prompt"])
        
        # Add banner-specific requirements
        prompt_parts.extend([
            "ultra wide banner format",
            "professional photography",
            "high quality",
            "detailed",
            "4K resolution"
        ])
        
        return ", ".join(prompt_parts)
    
    def _try_model(
        self,
        model_key: str,
        prompt: str
    ) -> Optional[Image.Image]:
        """Try generating with a specific model"""
        
        model_info = self.MODELS[model_key]
        
        try:
            logger.info(f"🎨 Trying {model_info['name']}...")
            
            # Create client with provider
            client = InferenceClient(
                provider=model_info["provider"],
                api_key=self.hf_token,
            )
            
            # Generate image (returns PIL.Image)
            image = client.text_to_image(
                prompt,
                model=model_info["model"]
            )
            
            logger.info(f"✅ Generated with {model_info['name']}")
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ {model_info['name']} failed: {e}")
            return None
    
    def generate_banner(
        self,
        category: str,
        style: str,
        element: Optional[str] = None,
        color_palette: str = "vibrant",
        num_variations: int = 3,
        preferred_model: Optional[str] = None
    ) -> List[bytes]:
        """Generate banner variations using HuggingFace InferenceClient (Synchronous)"""
        
        if not self.hf_token:
            raise Exception("Hugging Face token not configured")
        
        prompt = self.build_prompt(category, style, element, color_palette)
        logger.info(f"🎨 Generating banner with prompt: {prompt}")
        
        # Model priority list
        if preferred_model and preferred_model in self.MODELS:
            model_order = [preferred_model] + [k for k in self.MODELS.keys() if k != preferred_model]
        else:
            model_order = list(self.MODELS.keys())
        
        variations = []
        
        for i in range(num_variations):
            image_pil = None
            
            # Try each model until one works
            for model_key in model_order:
                image_pil = self._try_model(model_key, prompt)
                
                if image_pil:
                    logger.info(f"✅ Generated variation {i+1} using {self.MODELS[model_key]['name']}")
                    break
            
            if not image_pil:
                logger.error(f"❌ Failed to generate variation {i+1} with all models")
                continue
            
            # Process image to banner size (1920x480)
            try:
                target_width, target_height = 1920, 480
                img_ratio = image_pil.width / image_pil.height
                target_ratio = target_width / target_height
                
                if img_ratio > target_ratio:
                    # Image is wider, fit by height
                    new_height = target_height
                    new_width = int(new_height * img_ratio)
                    image_pil = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # Crop width
                    left = (new_width - target_width) // 2
                    image_pil = image_pil.crop((left, 0, left + target_width, target_height))
                else:
                    # Image is taller, fit by width
                    new_width = target_width
                    new_height = int(new_width / img_ratio)
                    image_pil = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    # Crop height
                    top = (new_height - target_height) // 2
                    image_pil = image_pil.crop((0, top, target_width, top + target_height))
                
                # Convert to bytes
                buffer = BytesIO()
                image_pil.save(buffer, format='JPEG', quality=95)
                variations.append(buffer.getvalue())
                
            except Exception as e:
                logger.error(f"❌ Failed to process image {i+1}: {e}")
                continue
        
        if not variations:
            raise Exception("Failed to generate any banner variations with all available models")
        
        logger.info(f"✅ Generated {len(variations)} banner variations")
        return variations
    
    @staticmethod
    def get_options() -> Dict:
        """Get all available options for frontend"""
        return {
            "models": [
                {
                    "id": model_id,
                    "name": model["name"],
                    "reliable": model.get("reliable", False),
                    "speed": model.get("speed", "medium")
                }
                for model_id, model in AIBannerGenerator.MODELS.items()
            ],
            "categories": [
                {
                    "id": cat_id,
                    "name": cat["name"],
                    "icon": cat["icon"]
                }
                for cat_id, cat in AIBannerGenerator.CATEGORIES.items()
            ],
            "styles": AIBannerGenerator.STYLES,
            "elements": AIBannerGenerator.CINEMA_ELEMENTS,
            "color_palettes": AIBannerGenerator.COLOR_PALETTES
        }


# Singleton instance
ai_banner_service = AIBannerGenerator()