# meetingsummary

## Project Overview:
The project aims to develop a Python-based AI script that generates summaries of meeting transcriptions from written text files. The script must utilize a locally installed Large Language Model (LLM), as we require an open-source solution that can be deployed on our Windows 11 PC with an Nvidia GPU and CUDA installed.

## Project Deliverables:

-    An AI script written in Python that can summarize meeting transcriptions.
-    Integration with an open-source LLM suitable for local deployment.
-    Documentation and support for the deployment and operation of the script.

# Meeting Summarizer

An intelligent meeting transcript summarization tool that processes both timestamped and plain text transcripts using LLMs.

## Features

- 🔍 Automatic format detection (timestamped/plain text)
- 📊 Smart chunking based on content and speakers
- ⚡ Efficient token management
- 🔄 Multi-stage summarization process
- 🌐 Works with local LLMs via Ollama
- 📝 Preserves chronological context
- 🎯 Extracts key decisions and action items

## Requirements

- Python 3.11
- Ollama installed and running
- Qwen 2.5 model pulled in Ollama
- NLTK data

## Quick Start


### Create and activate virtual environment

1. **Setup Environment**
   
### Install dependencies
Using poetry to manage dependencies. 

```
cd meetingsummary
pip install poetry
poetry install 

```

2. **Prepare Directory Structure**
```
meetingsummary/ 
  ├── meeting_summarizer/ 
  │ └── main.py 
  ├── transcripts/ # Put your transcript files here 
  │ └── your_meeting.txt 
  └── summaries/ # Generated summaries will be here
```


3. **Run the Summarizer**

```
cd meeting_summarizer
python main.py
```



## Input Format Support

### Timestamped Format
[00:00:00] Speaker A: Hello everyone
[00:00:05] Speaker B: Hi there

### Plain Text Format
Speaker A: Hello everyone
Speaker B: Hi there


## Output Format

The tool generates JSON files containing:
- Individual chunk summaries
- Final comprehensive summary
- Meeting metadata
- Key decisions and action items
- Timestamp information
## Configuration

Key parameters in `main.py`:
- `max_tokens`: Maximum tokens per chunk (default: 4000)
- `model_name`: LLM model name (default: "qwen2.5")
- `api_url`: Ollama API endpoint (default: "http://localhost:11434")

## Design Principles

1. **Robust Text Processing**
   - Automatic format detection
   - Smart chunking based on content semantics
   - Speaker-aware segmentation

2. **Context Preservation**
   - Maintains chronological order
   - Preserves speaker information
   - Retains timestamp context when available

3. **Efficient Processing**
   - Token-aware chunking
   - Rate limiting for API calls
   - Error handling and logging

## Limitations

- Requires local LLM setup via Ollama
- Processing speed depends on local hardware
- Maximum chunk size limited by LLM context window

## Contributing

Feel free to open issues or submit pull requests for:
- Bug fixes
- Feature additions
- Documentation improvements
- Performance optimizations

## License

MIT License - feel free to use and modify as needed.