import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip
import folder_paths
from tempfile import mkdtemp
import moviepy.editor as mp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

class CombineAudioVideoAndUpload:
    def __init__(self):
        self.drive_service = self.authenticate_google_drive()

    def authenticate_google_drive(self):
        """Authenticate and create a Google Drive API service."""
        SCOPES = ['https://www.googleapis.com/auth/drive']
        credentials_path = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)
        return build('drive', 'v3', credentials=credentials)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO", {"tooltip": "The input video file."}),  # Thay FILE thành VIDEO
                "audio": ("AUDIO", {"tooltip": "The input audio file."}),  # Thay FILE thành AUDIO
                "start_duration": ("FLOAT", {"default": 0, "tooltip": "The time (in seconds) the video starts before audio."}),
                "end_duration": ("FLOAT", {"default": 0, "tooltip": "The time (in seconds) the video ends after audio."})
            }
        }

    RETURN_TYPES = ("STRING", "FILE")
    RETURN_NAMES = ("file_url", "combined_video")
    FUNCTION = "combine_and_upload"
    OUTPUT_NODE = True
    CATEGORY = "video"

    def combine_video_audio(self, video_path, audio_path, start_duration, end_duration, output_path):
        """Combine video and audio, adjusting durations as specified."""
        video = mp.VideoFileClip(video_path)
        audio = mp.AudioFileClip(audio_path)

        adjusted_start = max(0, start_duration)
        adjusted_end = video.duration - (audio.duration + adjusted_start) + end_duration

        if adjusted_end < 0:
            adjusted_end = 0

        combined = video.subclip(adjusted_start, video.duration - adjusted_end).set_audio(audio)
        combined.write_videofile(output_path, codec="libx264", audio_codec="aac")

    def upload_to_google_drive(self, file_path):
        try:
            file_metadata = {'name': os.path.basename(file_path), 'parents': ['1fZyeDT_eW6ozYXhqi_qLVy-Xnu5JD67a']}
            media = MediaFileUpload(file_path, mimetype='video/mp4')
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            file_id = file.get('id')
            self.drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            return f"https://drive.google.com/uc?id={file_id}"
        except Exception as e:
            print(f"An error occurred while uploading to Google Drive: {e}")
            return None

    def combine_and_upload(self, video, audio, start_duration=0, end_duration=0):
        output_file = "/tmp/combined_output.mp4"

        self.combine_video_audio(video, audio, start_duration, end_duration, output_file)

        public_file_url = self.upload_to_google_drive(output_file)
        if not public_file_url:
            return ("", output_file)

        return (public_file_url, output_file)

class VideoAudioLoader:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "file_type": (["Video", "Audio"], {"default": "Video", "tooltip": "Select whether to load video or audio."}),
                "media": (sorted(files), {"file_upload": True, "tooltip": "Upload video or audio file from your computer."}),  # Nút để upload file
                "url": ("STRING", {"default": "", "tooltip": "Enter URL of the video or audio file (optional)."})
            }
        }

    CATEGORY = "media"
    RETURN_TYPES = ("VIDEO", "AUDIO")
    RETURN_NAMES = ("video_output", "audio_output")
    FUNCTION = "load_media"
    OUTPUT_NODE = True

    def download_file(self, url, file_type="video"):
        """Download video or audio file from URL."""
        try:
            response = requests.get(url)
            file_extension = "mp4" if file_type == "video" else "mp3"
            temp_dir = folder_paths.get_input_directory()
            file_name = os.path.join(temp_dir, f"downloaded_file.{file_extension}")
            with open(file_name, "wb") as file:
                file.write(response.content)
            return file_name
        except Exception as e:
            print(f"Error downloading file from {url}: {e}")
            return None

    def load_media(self, file_type="Video", media=None, url=""):
        file_path = None

        # Kiểm tra file upload hoặc URL
        if media:
            file_path = folder_paths.get_annotated_filepath(media)
        elif url:
            file_path = self.download_file(url, file_type=file_type.lower())
        else:
            raise ValueError("Either a file must be uploaded or a URL must be provided.")

        # Xử lý video hoặc audio tùy theo lựa chọn
        if file_type == "Video":
            video_clip = VideoFileClip(file_path)
            audio_clip = video_clip.audio
            return video_clip, audio_clip
        elif file_type == "Audio":
            audio_clip = AudioFileClip(file_path)
            return None, audio_clip

    @classmethod
    def IS_CHANGED(cls, media):
        file_path = folder_paths.get_annotated_filepath(media)
        return os.path.exists(file_path)

    @classmethod
    def VALIDATE_INPUTS(cls, media):
        if not folder_paths.exists_annotated_filepath(media):
            return "Invalid media file: {}".format(media)
        return True
            
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}
