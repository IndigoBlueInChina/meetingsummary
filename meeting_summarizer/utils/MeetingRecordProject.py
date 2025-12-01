import os
import json
from typing import List
from datetime import datetime


class MeetingRecordProject:
    """
    Class to represent a Meeting Record Project. This class manages the structure of the project,
    including handling audio files, transcriptions, summaries, and project metadata.
    """

    def __init__(self, project_name: str):
        """
        Initialize the project object without creating directories or initializing variables.
        This allows the create method to handle the initialization.
        
        :param project_name: The name of the project, used for naming the root directory.
        """
        self.project_name = project_name
        self._project_dir = None
        self.record_file = None
        self.transcript_file = None
        self.summary_file = None
        self.metadata = {}

    @property
    def project_dir(self):
        """项目根目录"""
        if not self._project_dir:
            from config.settings import Settings
            settings = Settings()
            base_dir = settings.config_dir / "projects"
            base_dir.mkdir(parents=True, exist_ok=True)
            self._project_dir = str(base_dir / self.project_name)
        return self._project_dir

    @property
    def audio_dir(self):
        """音频文件目录"""
        return os.path.join(self.project_dir, "audio")

    @property
    def transcript_dir(self):
        """转写文件目录"""
        return os.path.join(self.project_dir, "transcript")

    @property
    def summary_dir(self):
        """总结文件目录"""
        return os.path.join(self.project_dir, "summary")

    @property
    def project_info_path(self):
        """项目信息文件路径"""
        return os.path.join(self.project_dir, "project_info.json")

    @property
    def metadata_path(self):
        """元数据文件路径"""
        return os.path.join(self.project_dir, "metadata.json")

    def create(self):
        """
        This method is responsible for initializing all variables and creating the necessary directories 
        and project structure.
        """
        # Create the necessary directories if they don't exist
        self._create_directories()

        # Initialize project metadata
        self.metadata = {
            "project_name": self.project_name,
            "project_summary": "",
            "files": {
                "audio": "",
                "transcript": "",
                "proofread_transcript": "",
                "summaries": []
            }
        }

    def _create_directories(self):
        """
        Creates the necessary subdirectories (audio, transcript, summary) 
        for the project if they don't already exist.
        """
        # Ensure the project directory exists
        os.makedirs(self.project_dir, exist_ok=True)
        
        # Create subdirectories for audio, transcript, and summaries
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.transcript_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)

    def add_audio(self, audio_file_path: str):
        """
        Add the audio file to the project. 
        If an audio file already exists, it will be replaced.
        
        :param audio_file_path: The path to the audio file (MP3, WAV, Opus).
        """
        # 如果已存在音频文件，先删除旧文件
        if self.metadata['files']['audio']:
            old_audio = self.metadata['files']['audio']
            if os.path.exists(old_audio):
                print(f"[MeetingRecordProject] 警告：已存在音频文件，将被覆盖: {old_audio}")
                try:
                    os.remove(old_audio)
                    print(f"[MeetingRecordProject] 已删除旧音频文件")
                except Exception as e:
                    print(f"[MeetingRecordProject] 删除旧音频文件失败: {str(e)}")
        
        # Copy or move the audio file to the audio directory
        audio_file_name = os.path.basename(audio_file_path)
        target_path = os.path.join(self.audio_dir, audio_file_name)
        
        # 如果源文件和目标文件相同，无需移动
        if os.path.abspath(audio_file_path) != os.path.abspath(target_path):
            # 如果目标文件已存在，先删除
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(audio_file_path, target_path)
        
        self.metadata['files']['audio'] = target_path
        self._save_project_metadata()
        print(f"[MeetingRecordProject] 音频文件已保存: {target_path}")

    def add_transcript(self, transcript_file_path: str):
        """
        Add a transcription file (txt, docx, or pdf) to the project. 
        If a transcript already exists, it will be replaced.
        
        :param transcript_file_path: The path to the transcript file.
        """
        # 如果已存在转写文件，先删除旧文件
        if self.metadata['files']['transcript']:
            old_transcript = self.metadata['files']['transcript']
            if os.path.exists(old_transcript):
                print(f"[MeetingRecordProject] 警告：已存在转写文件，将被覆盖: {old_transcript}")
                try:
                    os.remove(old_transcript)
                    print(f"[MeetingRecordProject] 已删除旧转写文件")
                except Exception as e:
                    print(f"[MeetingRecordProject] 删除旧转写文件失败: {str(e)}")
        
        # Copy or move the transcript file to the transcript directory
        transcript_file_name = os.path.basename(transcript_file_path)
        target_path = os.path.join(self.transcript_dir, transcript_file_name)
        
        # 如果源文件和目标文件相同，无需移动
        if os.path.abspath(transcript_file_path) != os.path.abspath(target_path):
            # 如果目标文件已存在，先删除
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(transcript_file_path, target_path)
        
        self.metadata['files']['transcript'] = target_path
        self._save_project_metadata()
        print(f"[MeetingRecordProject] 转写文件已保存: {target_path}")

    def add_proofread_transcript(self, transcript_md_path: str):
        """
        Add the proofread version of the transcript in Markdown format to the project.
        
        :param transcript_md_path: The path to the Markdown-formatted transcript.
        """
        transcript_md_name = os.path.basename(transcript_md_path)
        os.rename(transcript_md_path, os.path.join(self.transcript_dir, transcript_md_name))
        self.metadata['files']['proofread_transcript'] = os.path.join(self.transcript_dir, transcript_md_name)
        self._save_project_metadata()

    def add_summary(self, summary_file_path: str):
        """
        Add a summary file in Markdown format to the project. Summaries are versioned (e.g., summary_v001.md).
        
        :param summary_file_path: The path to the summary Markdown file.
        """
        summary_file_name = os.path.basename(summary_file_path)
        os.rename(summary_file_path, os.path.join(self.summary_dir, summary_file_name))
        
        # Append the summary to the summaries list
        self.metadata['files']['summaries'].append(os.path.join(self.summary_dir, summary_file_name))
        self._save_project_metadata()

    def _save_project_metadata(self):
        """
        Saves the project metadata to the `project_info.json` file.
        This includes project name, summary, and the file paths of the audio, transcript, and summaries.
        """
        with open(self.project_info_path, 'w') as json_file:
            json.dump(self.metadata, json_file, indent=4)

    def load_project_metadata(self):
        """
        Loads the project metadata from the `project_info.json` file.
        """
        if os.path.exists(self.project_info_path):
            with open(self.project_info_path, 'r') as json_file:
                self.metadata = json.load(json_file)

    def set_project_summary(self, summary: str):
        """
        Set or update the project summary in the metadata. Typically generated by an LLM.
        
        :param summary: The project summary text.
        """
        self.metadata['project_summary'] = summary
        self._save_project_metadata()

    def get_project_info(self) -> dict:
        """
        Get the current project metadata, including file paths and summary information.
        
        :return: Dictionary containing project metadata.
        """
        return self.metadata

    # File fetching methods:

    def get_audio_filename(self) -> str:
        """
        Get the full path to the audio file for this project.
        Returns an empty string if the audio file does not exist.
        
        :return: Full path to the audio file, or an empty string if the file is not present.
        """
        return self.metadata['files']['audio'] if self.metadata['files']['audio'] else ""

    def get_transcript_filename(self) -> str:
        """
        Get the full path to the transcript file for this project.
        Returns an empty string if the transcript file does not exist.
        
        :return: Full path to the transcript file, or an empty string if the file is not present.
        """
        return self.metadata['files']['transcript'] if self.metadata['files']['transcript'] else ""

    def get_proofread_transcript_filename(self) -> str:
        """
        Get the full path to the proofread transcript in Markdown format.
        Returns an empty string if the file does not exist.
        
        :return: Full path to the proofread transcript file, or an empty string if the file is not present.
        """
        return self.metadata['files']['proofread_transcript'] if self.metadata['files']['proofread_transcript'] else ""

    def get_summary_filename(self) -> str:
        """
        Get the full path to the latest summary file for this project.
        Returns an empty string if no summary file exists.
        
        :return: Full path to the latest summary file, or an empty string if no summary is present.
        """
        summaries = self.metadata['files']['summaries']
        return summaries[-1] if summaries else ""

    def get_summary_new_filename(self) -> str:
        """
        Get the path to a new summary file that will be saved in the summary directory, 
        with the next available version number (e.g., summary_v003.md).
        
        :return: Full path to the new summary file with the appropriate version number.
        """
        summaries = self.metadata['files']['summaries']
        new_version = len(summaries) + 1  # Versioning based on the number of existing summaries
        new_filename = f"summary_v{new_version:03}.md"
        return os.path.join(self.summary_dir, new_filename)

    def get_transcript_new_filename(self) -> str:
        """
        Get the path to a new transcript file that will be saved in the transcript directory.
        The file name will include the current timestamp (hours, minutes, and seconds) to ensure uniqueness.
        
        :return: Full path to a new transcript file with a timestamp.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"transcript_{timestamp}.txt"
        return os.path.join(self.transcript_dir, new_filename)

    def get_audio_new_filename(self) -> str:
        """
        Get the path to a new audio file that will be saved in the audio directory.
        The file name will include the current timestamp (hours,minutes, and seconds) to ensure uniqueness.
        
        :return: Full path to a new audio file with a timestamp.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"audio_{timestamp}.wav"
        return os.path.join(self.audio_dir, new_filename)
    
