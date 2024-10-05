import os
import tempfile
import hashlib  # Thêm import này
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

class CombineAudioVideoAndUpload:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'
    DRIVE_FOLDER_ID = '1fZyeDT_eW6ozYXhqi_qLVy-Xnu5JD67a'
    
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
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Drive service: {str(e)}")
            raise RuntimeError(f"Failed to initialize Drive service: {str(e)}")
            
    def _upload_to_drive(self, file_path):
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

            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()

            file_id = file.get('id')
            return f"https://drive.google.com/uc?id={file_id}"

        except Exception as e:
            raise RuntimeError(f"Failed to upload to Drive: {str(e)}")

    def combine_and_upload(self, video, audio, start_duration, end_duration):
        """
        Kết hợp video và audio, sau đó upload lên Drive.
        """
        try:
            # Debug: In loại dữ liệu và giá trị của video và audio
            print(f"Video input type: {type(video)}")
            print(f"Audio input type: {type(audio)}")
            print(f"Video input: {video}")
            print(f"Audio input: {audio}")

            # Kiểm tra xem video có đúng định dạng và chứa 'path' không
            if isinstance(video, dict) and 'path' in video:
                video_clip = VideoFileClip(video['path'])
            else:
                raise TypeError(f"Invalid video input: {video}")

            # Kiểm tra xem audio có đúng định dạng và chứa 'path' không
            if isinstance(audio, dict) and 'path' in audio:
                audio_clip = AudioFileClip(audio['path'])
            else:
                raise TypeError(f"Invalid audio input: {audio}")

            # Xử lý phần còn lại như bình thường
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                temp_output_path = temp_output.name

                total_duration = audio_clip.duration + start_duration + end_duration
                if video_clip.duration < total_duration:
                    video_clip = video_clip.loop(duration=total_duration)
                else:
                    video_clip = video_clip.subclip(0, total_duration)

                audio_clip = audio_clip.set_start(start_duration)
                final_clip = CompositeVideoClip([video_clip])
                final_clip = final_clip.set_audio(audio_clip)

                final_clip.write_videofile(
                    temp_output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=temp_output_path.replace('.mp4', '.wav'),
                    remove_temp=True
                )

                drive_url = self._upload_to_drive(temp_output_path)

                video_clip.close()
                audio_clip.close()
                final_clip.close()

                with open(temp_output_path, 'rb') as f:
                    combined_video = {'path': temp_output_path, 'data': f.read()}

                return (drive_url, combined_video)

        except Exception as e:
            raise RuntimeError(f"Failed to combine video and audio: {str(e)}")

        finally:
            for path in [temp_output_path]:
                if os.path.exists(path):
                    os.unlink(path)

    @classmethod
    def IS_CHANGED(s, video, audio, start_duration, end_duration):
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

            
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}
