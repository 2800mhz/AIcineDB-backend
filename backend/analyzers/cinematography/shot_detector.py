"""
Shot Detection Module
Detects shots, extracts keyframes, and classifies shot types
"""
import logging
from typing import List, Dict, Tuple
from pathlib import Path
import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False
    logger.warning("PySceneDetect not available")


class ShotDetector:
    """Detect shots and extract keyframes from video"""
    
    def __init__(self, threshold: float = 27.0):
        """
        Args:
            threshold: Content detection threshold (lower=more sensitive)
        """
        self.threshold = threshold
    
    def detect_shots(self, video_path: str, output_dir: str = None) -> List[Dict]:
        """
        Detect shots in video and extract keyframes
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save keyframes
            
        Returns:
            List of shot dictionaries with timing and metadata
        """
        if not SCENEDETECT_AVAILABLE:
            logger.warning("Using fallback shot detection")
            return self._detect_shots_fallback(video_path, output_dir)
        
        try:
            logger.info(f"🎬 Detecting shots in video...")
            
            # Setup video manager
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=self.threshold))
            
            # Detect scenes
            video_manager.start()
            scene_manager.detect_scenes(video=video_manager)
            scene_list = scene_manager.get_scene_list()
            video_manager.release()
            
            shots = []
            
            # Process each shot
            for i, scene in enumerate(scene_list):
                start_frame, end_frame = scene
                start_time = start_frame.get_seconds()
                end_time = end_frame.get_seconds()
                duration = end_time - start_time
                
                shot_data = {
                    'shot_number': i + 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'start_frame': start_frame.get_frames(),
                    'end_frame': end_frame.get_frames(),
                }
                
                # Extract keyframe if output_dir provided
                if output_dir:
                    keyframe_path = self._extract_keyframe(
                        video_path,
                        start_time,
                        output_dir,
                        i + 1
                    )
                    shot_data['keyframe_path'] = keyframe_path
                    
                    # Analyze keyframe
                    analysis = self._analyze_keyframe(keyframe_path)
                    shot_data.update(analysis)
                
                shots.append(shot_data)
            
            logger.info(f"✓ Detected {len(shots)} shots")
            
            return shots
            
        except Exception as e:
            logger.error(f"Shot detection failed: {e}")
            return self._detect_shots_fallback(video_path, output_dir)
    
    def _detect_shots_fallback(self, video_path: str, output_dir: str = None) -> List[Dict]:
        """Fallback shot detection using frame differencing"""
        logger.info("Using fallback frame difference method...")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        shots = []
        prev_frame = None
        shot_start = 0
        shot_num = 1
        frame_num = 0
        
        threshold = 30.0  # Difference threshold
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if prev_frame is not None:
                # Calculate frame difference
                gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(gray1, gray2)
                diff_mean = np.mean(diff)
                
                # Shot boundary detected
                if diff_mean > threshold:
                    shot_end = frame_num / fps
                    
                    shots.append({
                        'shot_number': shot_num,
                        'start_time': shot_start,
                        'end_time': shot_end,
                        'duration': shot_end - shot_start,
                        'shot_type': 'unknown',
                        'lighting': 'unknown',
                    })
                    
                    shot_start = shot_end
                    shot_num += 1
            
            prev_frame = frame.copy()
            frame_num += 1
        
        cap.release()
        
        # Add final shot
        if shot_num == 1 or (frame_num / fps - shot_start) > 1.0:
            shots.append({
                'shot_number': shot_num,
                'start_time': shot_start,
                'end_time': frame_num / fps,
                'duration': frame_num / fps - shot_start,
                'shot_type': 'unknown',
                'lighting': 'unknown',
            })
        
        logger.info(f"✓ Detected {len(shots)} shots (fallback method)")
        return shots
    
    def _extract_keyframe(
        self,
        video_path: str,
        timestamp: float,
        output_dir: str,
        shot_number: int
    ) -> str:
        """Extract keyframe at specific timestamp"""
        output_path = Path(output_dir) / f"shot_{shot_number:04d}.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(timestamp * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(str(output_path), frame)
            return str(output_path)
        
        return None
    
    def _analyze_keyframe(self, image_path: str) -> Dict:
        """Analyze keyframe for lighting, colors, etc."""
        try:
            img = cv2.imread(image_path)
            
            # Brightness
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray) / 255.0
            
            # Lighting classification
            if brightness < 0.3:
                lighting = "low-key"
            elif brightness > 0.7:
                lighting = "high-key"
            else:
                lighting = "normal"
            
            # Color extraction (dominant colors)
            colors = self._extract_dominant_colors(img)
            
            # Shot type estimation (based on resolution and composition)
            shot_type = self._estimate_shot_type(img)
            
            return {
                'brightness': float(brightness),
                'lighting': lighting,
                'colors': colors,
                'shot_type': shot_type,
            }
            
        except Exception as e:
            logger.error(f"Keyframe analysis failed: {e}")
            return {
                'brightness': 0.5,
                'lighting': 'unknown',
                'colors': [],
                'shot_type': 'unknown',
            }
    
    def _extract_dominant_colors(self, img: np.ndarray, n_colors: int = 5) -> List[str]:
        """Extract dominant colors from image"""
        try:
            # Resize for speed
            img_small = cv2.resize(img, (100, 100))
            img_rgb = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)
            
            # Reshape to pixel array
            pixels = img_rgb.reshape(-1, 3)
            
            # K-means clustering
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get dominant colors
            colors = []
            for color in kmeans.cluster_centers_:
                hex_color = '#{:02x}{:02x}{:02x}'.format(
                    int(color[0]), int(color[1]), int(color[2])
                )
                colors.append(hex_color)
            
            return colors
            
        except ImportError:
            # Fallback: simple color histogram
            colors = []
            for channel in cv2.split(img):
                mean_val = int(np.mean(channel))
                colors.append(f"#{mean_val:02x}{mean_val:02x}{mean_val:02x}")
            return colors[:n_colors]
    
    def _estimate_shot_type(self, img: np.ndarray) -> str:
        """Estimate shot type based on image characteristics"""
        height, width = img.shape[:2]
        
        # Edge detection for composition analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # Simple heuristics
        if edge_density < 0.05:
            return "close-up"
        elif edge_density < 0.15:
            return "medium"
        else:
            return "wide"
    
    def calculate_shot_statistics(self, shots: List[Dict]) -> Dict:
        """Calculate statistics about shots"""
        if not shots:
            return {}
        
        durations = [s['duration'] for s in shots]
        
        return {
            'total_shots': len(shots),
            'avg_shot_length': np.mean(durations),
            'median_shot_length': np.median(durations),
            'min_shot_length': np.min(durations),
            'max_shot_length': np.max(durations),
            'std_shot_length': np.std(durations),
        }
