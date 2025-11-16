"""
Visual Style Classification using CLIP
Classifies visual style and generates embeddings for similarity
"""
import logging
from typing import List, Dict, Tuple
from pathlib import Path
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP not available")


class StyleClassifier:
    """CLIP-based visual style classifier"""
    
    # Visual style categories
    STYLE_LABELS = [
        "anime style animation",
        "realistic live action",
        "3D CGI animation",
        "2D cartoon style",
        "stop motion animation",
        "documentary footage",
        "noir black and white",
        "vibrant colorful",
        "cyberpunk neon",
        "vintage film",
        "modern digital",
        "cinematic film",
        "vlog handheld",
        "professional studio",
    ]
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        Initialize CLIP model
        
        Args:
            model_name: HuggingFace model identifier
        """
        if not CLIP_AVAILABLE:
            logger.warning("CLIP not available, using dummy classifier")
            self.model = None
            self.processor = None
            return
        
        try:
            logger.info(f"Loading CLIP model: {model_name}")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            logger.info(f"✓ CLIP loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            self.model = None
            self.processor = None
    
    def classify_style(self, image_paths: List[str], top_k: int = 3) -> Dict:
        """
        Classify visual style from keyframes
        
        Args:
            image_paths: List of keyframe paths
            top_k: Return top K style predictions
            
        Returns:
            Dict with style predictions and confidence scores
        """
        if not self.model:
            return self._dummy_classification()
        
        try:
            logger.info(f"🎨 Classifying visual style from {len(image_paths)} frames...")
            
            # Load and process images
            images = []
            for path in image_paths[:10]:  # Limit to 10 frames for speed
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")
            
            if not images:
                return self._dummy_classification()
            
            # Prepare inputs
            inputs = self.processor(
                text=self.STYLE_LABELS,
                images=images,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Average across frames
            avg_probs = probs.mean(dim=0).cpu().numpy()
            
            # Get top K styles
            top_indices = np.argsort(avg_probs)[-top_k:][::-1]
            
            styles = []
            for idx in top_indices:
                styles.append({
                    'style': self.STYLE_LABELS[idx],
                    'confidence': float(avg_probs[idx])
                })
            
            # Generate style fingerprint
            fingerprint = self._generate_fingerprint(styles)
            
            logger.info(f"✓ Top style: {styles[0]['style']} ({styles[0]['confidence']:.2%})")
            
            return {
                'styles': styles,
                'fingerprint': fingerprint,
                'top_style': styles[0]['style'],
                'confidence': styles[0]['confidence'],
            }
            
        except Exception as e:
            logger.error(f"Style classification failed: {e}")
            return self._dummy_classification()
    
    def generate_visual_embedding(self, image_paths: List[str]) -> np.ndarray:
        """
        Generate visual embedding for similarity search
        
        Args:
            image_paths: List of keyframe paths
            
        Returns:
            512-dim embedding vector
        """
        if not self.model:
            return np.random.randn(512).astype(np.float32)
        
        try:
            logger.info("🔢 Generating visual embedding...")
            
            # Load images
            images = []
            for path in image_paths[:20]:  # Use up to 20 frames
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                except:
                    continue
            
            if not images:
                return np.random.randn(512).astype(np.float32)
            
            # Process images
            inputs = self.processor(
                images=images,
                return_tensors="pt"
            ).to(self.device)
            
            # Get image embeddings
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Average embeddings across frames
                embedding = image_features.mean(dim=0).cpu().numpy()
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            logger.info(f"✓ Generated {len(embedding)}-dim embedding")
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return np.random.randn(512).astype(np.float32)
    
    def _generate_fingerprint(self, styles: List[Dict]) -> str:
        """Generate human-readable style fingerprint"""
        # Take top 3 styles and create fingerprint
        top_styles = [s['style'].split()[0] for s in styles[:3]]
        return "-".join(top_styles).lower()
    
    def _dummy_classification(self) -> Dict:
        """Dummy classification when CLIP unavailable"""
        return {
            'styles': [
                {'style': 'modern digital', 'confidence': 0.6},
                {'style': 'cinematic film', 'confidence': 0.3},
                {'style': 'vibrant colorful', 'confidence': 0.1},
            ],
            'fingerprint': 'modern-cinematic-vibrant',
            'top_style': 'modern digital',
            'confidence': 0.6,
        }
    
    def analyze_color_palette(self, image_paths: List[str]) -> Dict:
        """Analyze color palette across frames"""
        try:
            from collections import Counter
            
            all_colors = []
            
            for path in image_paths[:10]:
                try:
                    img = Image.open(path).convert("RGB")
                    img_small = img.resize((50, 50))
                    pixels = list(img_small.getdata())
                    
                    # Quantize colors
                    for r, g, b in pixels:
                        # Round to nearest 32
                        r = (r // 32) * 32
                        g = (g // 32) * 32
                        b = (b // 32) * 32
                        all_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                except:
                    continue
            
            if not all_colors:
                return {'palette': [], 'dominant_hue': 'unknown'}
            
            # Get most common colors
            color_counts = Counter(all_colors)
            top_colors = [color for color, _ in color_counts.most_common(5)]
            
            # Determine dominant hue
            dominant_hue = self._classify_hue(top_colors[0] if top_colors else "#808080")
            
            return {
                'palette': top_colors,
                'dominant_hue': dominant_hue,
            }
            
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {'palette': [], 'dominant_hue': 'unknown'}
    
    def _classify_hue(self, hex_color: str) -> str:
        """Classify color into hue category"""
        # Simple hue classification
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        
        if r > g and r > b:
            return "warm" if r > 150 else "dark"
        elif b > r and b > g:
            return "cool"
        elif g > r and g > b:
            return "neutral"
        else:
            if (r + g + b) / 3 > 150:
                return "bright"
            else:
                return "dark"
