import os
import tempfile
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

class CombineAudioVideoAndUpload:
    """
    Node để kết hợp video và audio, sau đó upload lên Google Drive.
    
    Attributes:
        SCOPES (list): Google Drive API scopes needed
        CREDENTIALS_FILE (str): Path to credentials file
        TOKEN_FILE (str): Path to token file
        DRIVE_FOLDER_ID (str): Google Drive folder ID to upload to
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    CREDENTIALS_FILE = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'  # Thay đổi path này
    TOKEN_FILE = 'token.pickle'
    DRIVE_FOLDER_ID = '1fZyeDT_eW6ozYXhqi_qLVy-Xnu5JD67a'  # Thay đổi folder ID này

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("VIDEO",),
                "audio": ("AUDIO",),
                "start_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "end_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                })
            }
        }

    RETURN_TYPES = ("STRING", "VIDEO",)
    RETURN_NAMES = ("file_url", "combined_video",)
    FUNCTION = "combine_and_upload"
    CATEGORY = "video/audio"

    def __init__(self):
        self.drive_service = None
        self._initialize_drive_service()

    def _initialize_drive_service(self):
        """Khởi tạo Google Drive service."""
        creds = None
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        self.drive_service = build('drive', 'v3', credentials=creds)

    def _upload_to_drive(self, file_path):
        """Upload file lên Google Drive và trả về direct link."""
        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.DRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # Cập nhật permission để file public
            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()

            # Tạo direct link
            file_id = file.get('id')
            return f"https://drive.google.com/uc?id={file_id}"

        except Exception as e:
            raise RuntimeError(f"Failed to upload to Drive: {str(e)}")

    def combine_and_upload(self, video, audio, start_duration, end_duration):
        """
        Kết hợp video và audio, sau đó upload lên Drive.
        
        Args:
            video: Video input từ node LoadVideo
            audio: Audio input từ node LoadAudio
            start_duration: Thời gian delay trước khi audio bắt đầu (seconds)
            end_duration: Thời gian video tiếp tục sau khi audio kết thúc (seconds)
        
        Returns:
            tuple: (drive_url, combined_video)
        """
        try:
            # Tạo temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video, \
                 tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio, \
                 tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                
                # Lưu video và audio vào temporary files
                temp_video_path = temp_video.name
                temp_audio_path = temp_audio.name
                temp_output_path = temp_output.name

                # Xử lý video input
                video_clip = VideoFileClip(video['path'])
                
                # Xử lý audio input
                audio_clip = AudioFileClip(audio['path'])
                
                # Tính toán duration
                total_duration = audio_clip.duration + start_duration + end_duration
                
                # Nếu video ngắn hơn total_duration, loop video
                if video_clip.duration < total_duration:
                    video_clip = video_clip.loop(duration=total_duration)
                else:
                    # Cắt video cho khớp với total_duration
                    video_clip = video_clip.subclip(0, total_duration)

                # Set audio start time
                audio_clip = audio_clip.set_start(start_duration)

                # Combine video và audio
                final_clip = CompositeVideoClip([video_clip])
                final_clip = final_clip.set_audio(audio_clip)

                # Write ra file
                final_clip.write_videofile(
                    temp_output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=temp_audio_path,
                    remove_temp=True
                )

                # Upload lên Drive
                drive_url = self._upload_to_drive(temp_output_path)

                # Cleanup
                video_clip.close()
                audio_clip.close()
                final_clip.close()

                # Đọc file output để return
                with open(temp_output_path, 'rb') as f:
                    combined_video = {'path': temp_output_path, 'data': f.read()}

                return (drive_url, combined_video)

        except Exception as e:
            raise RuntimeError(f"Failed to combine video and audio: {str(e)}")

        finally:
            # Cleanup temporary files
            for path in [temp_video_path, temp_audio_path, temp_output_path]:
                if os.path.exists(path):
                    os.unlink(path)

    @classmethod
    def IS_CHANGED(s, video, audio, start_duration, end_duration):
        """
        Kiểm tra xem có cần render lại video không.
        """
        # Generate hash từ tất cả inputs
        m = hashlib.sha256()
        m.update(str(video).encode())
        m.update(str(audio).encode())
        m.update(str(start_duration).encode())
        m.update(str(end_duration).encode())
        return m.digest().hex()

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
        video_data = self.download_file(video_url)
        return (video_data,)  # Trả về video đã tải

    def download_file(self, url):
        # Logic để tải file từ URL
        import requests
        response = requests.get(url)
        return response.content  # Trả về nội dung của video

# Thêm các định nghĩa cho node
NODE_CLASS_MAPPINGS = {
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoAudioLoader": "Video Loader"
}


            
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}
