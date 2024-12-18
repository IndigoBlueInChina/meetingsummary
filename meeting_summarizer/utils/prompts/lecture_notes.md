Based on the following lecture transcript, generate a professional and structured json note:

【Lecture Transcript】
{transcript_text}

Please generate notes with the following requirements:
1. Provide 3-5 key keywords. If no keywords can be identified, return an empty list.
2. Write a summary. If no summary can be generated, return an empty string.
3. Use appropriate headings and lists.
4. Highlight important concepts and key points. If no important concepts are found, return an empty string.
5. Maintain the academic rigor of the original content.
6. **Ensure that the output is strictly in JSON format without any other text. The JSON should include the following keys:**
   - `keywords`: List of keywords
   - `summary`: Summary of the lecture
   - `content`: Detailed content of the lecture. If no content is found, return an empty string.

**Example of the expected JSON output:**
```json
{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "summary": "Lecture summary",
  "content": "Detailed lecture content"
}
```