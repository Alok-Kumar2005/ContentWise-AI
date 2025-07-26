import videodb
from videodb import SearchType, IndexType
import logging
from config import Config

class VideoDBService:
    def __init__(self):
        self.conn = videodb.connect(api_key=Config.VIDEODB_API_KEY)
        self.collection = self.conn.get_collection()
        
    def upload_video(self, source, source_type="url"):
        """Upload video from URL or file path"""
        try:
            if source_type == "url":
                video = self.conn.upload(url=source)
            else:
                video = self.conn.upload(file_path=source)
            
            # Index the video for search
            video.index_spoken_words()
            video.index_scenes(prompt="General video scenes and activities")
            
            return video
        except Exception as e:
            logging.error(f"Error uploading video: {e}")
            raise
    
    def get_transcript(self, video):
        """Get video transcript"""
        try:
            return video.get_transcript_text()
        except Exception as e:
            logging.error(f"Error getting transcript: {e}")
            return ""
    
    def search_video_content(self, video, query):
        """Search for specific content in video"""
        try:
            results = video.search(
                query=query,
                search_type=SearchType.semantic,
                index_type=IndexType.spoken_word
            )
            
            shots = results.get_shots()
            timestamps = [(shot.start, shot.end) for shot in shots]
            
            return {
                "results": shots,
                "timestamps": timestamps,
                "playable_url": results.play()
            }
        except Exception as e:
            logging.error(f"Error searching video: {e}")
            return {"results": [], "timestamps": [], "playable_url": None}