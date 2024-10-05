import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip
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
    def __init__(self):
        # Tạo thư mục tạm để lưu file tạm thời
        self.temp_dir = mkdtemp()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": "", "tooltip": "URL of the video or audio file."}),  # Ô để nhập URL
                # "FILE" được thay bằng "FILE_UPLOAD" để tạo nút upload file
                "file_upload": ("FILE_UPLOAD", {"tooltip": "Upload a video or audio file from your computer."}),
            }
        }

    RETURN_TYPES = ("VIDEO", "AUDIO")
    RETURN_NAMES = ("video_output", "audio_output")
    FUNCTION = "load_media"
    OUTPUT_NODE = True
    CATEGORY = "media"

    def download_file(self, url, file_type="video"):
        """Download video or audio file from URL."""
        try:
            # Tải nội dung từ URL
            response = requests.get(url)
            file_extension = "mp4" if file_type == "video" else "mp3"
            # Lưu file tạm thời trong thư mục temp
            file_name = os.path.join(self.temp_dir, f"downloaded_file.{file_extension}")
            with open(file_name, "wb") as file:
                file.write(response.content)
            return file_name
        except Exception as e:
            print(f"Error downloading file from {url}: {e}")
            return None

    def load_media(self, url="", file_upload=None):
        """Load video/audio from URL or uploaded file."""
        file_type = None
        file_path = None

        # Kiểm tra URL hoặc file upload
        if url:
            if url.endswith(".mp4"):
                file_type = "video"
            elif url.endswith(".mp3"):
                file_type = "audio"
            else:
                raise ValueError("Unsupported file type in URL")
            file_path = self.download_file(url, file_type=file_type)
        elif file_upload:
            file_path = file_upload
            if file_upload.endswith(".mp4"):
                file_type = "video"
            elif file_upload.endswith(".mp3"):
                file_type = "audio"
            else:
                raise ValueError("Unsupported file type in upload")
        else:
            raise ValueError("Either URL or upload must be provided")

        # Xử lý file video hoặc audio
        if file_type == "video":
            video_clip = VideoFileClip(file_path)
            audio_clip = video_clip.audio
            return video_clip, audio_clip
        elif file_type == "audio":
            audio_clip = AudioFileClip(file_path)
            return None, audio_clip
            
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}
