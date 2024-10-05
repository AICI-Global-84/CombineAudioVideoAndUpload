import os
import requests
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
                "video": ("VIDEO", {"tooltip": "The input video file."}),
                "audio": ("AUDIO", {"tooltip": "The input audio file."}),
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

    def download_file(self, url):
        """Download file from the given URL and return the local filename."""
        local_filename = url.split('/')[-1]
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        return local_filename

    def combine_and_upload(self, video, audio, start_duration=0, end_duration=0):
        output_file = "/tmp/combined_output.mp4"

        # Kiểm tra kiểu dữ liệu và tải file nếu cần
        if isinstance(video, str) and video.startswith('http'):
            video = self.download_file(video)
        
        if isinstance(audio, str) and audio.startswith('http'):
            audio = self.download_file(audio)

        if not isinstance(video, str) or not isinstance(audio, str):
            raise ValueError("video and audio must be of type str.")

        self.combine_video_audio(video, audio, start_duration, end_duration, output_file)

        public_file_url = self.upload_to_google_drive(output_file)
        if not public_file_url:
            return ("", output_file)

        return (public_file_url, output_file)

class VideoAudioLoader:
    """
    Node để tải video từ URL

    Class methods
    -------------
    INPUT_TYPES (dict):
        Định nghĩa các tham số đầu vào cho node.

    Attributes
    ----------
    RETURN_TYPES (`tuple`):
        Kiểu dữ liệu cho mỗi phần tử trong tuple đầu ra.
    RETURN_NAMES (`tuple`):
        Tên tùy chọn cho mỗi đầu ra trong tuple đầu ra.
    FUNCTION (`str`):
        Tên phương thức entry-point. Ví dụ, nếu `FUNCTION = "load"`, thì nó sẽ chạy VideoAudioLoader().load()
    OUTPUT_NODE ([`bool`]):
        Nếu node này là một output node để xuất kết quả từ đồ thị.
    CATEGORY (`str`):
        Danh mục mà node nên xuất hiện trong giao diện.
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_url": ("STRING", {
                    "multiline": False,
                    "default": "http://example.com/video.mp4",
                    "lazy": True
                }),
            },
        }

    RETURN_TYPES = ("VIDEO",)  # Kiểu đầu ra là VIDEO
    FUNCTION = "load"          # Tên phương thức entry-point
    CATEGORY = "Media Loader"   # Danh mục cho node

    def load(self, video_url):
        # Logic tải video từ URL
        video_path = self.download_file(video_url)
        return (video_path,)  # Trả về đường dẫn của video đã tải

    def download_file(self, url):
        # Logic để tải file từ URL
        local_filename = url.split('/')[-1]  # Lấy tên file từ URL
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        return local_filename  # Trả về đường dẫn đến file đã tải


            
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}
