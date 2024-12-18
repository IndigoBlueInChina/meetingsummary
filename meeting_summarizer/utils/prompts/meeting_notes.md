Generate comprehensive meeting notes based on the following transcript:

【Meeting Transcript】
{transcript_text}

Requirements for note generation:
1. Extract 3-5 key keywords that capture the essence of the meeting. If no keywords can be identified, return an empty list.
2. Write a concise summary highlighting key outcomes. If no summary can be generated, return an empty string.
3. Structure notes with:
   - Main discussion points. If none are found, return an empty list.
   - Key decisions made. If no decisions are made, return an empty list.
   - Action items with responsible parties. If there are no action items, return an empty list. Do not add any other text.
   - Follow-up recommendations. If there are no recommendations, return an empty list. Do not add any other text.

**Please return the response in a strict JSON format with these fields without any other text:**
- `keywords`: List of keywords
- `summary`: Meeting summary
- `key_discussion_points`: Bulleted list of main discussion topics
- `decisions`: Bulleted list of key decisions
- `action_items`: List of actions with owner and deadline
- `next_steps`: Recommendations for follow-up

Ensure the notes are professional, clear, and actionable, and do not include any information not present in the transcript.

**Example of the expected JSON output:**
```json
{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "summary": "Meeting summary",
  "key_discussion_points": ["Point 1", "Point 2", "Point 3"],
  "decisions": ["Decision 1", "Decision 2", "Decision 3"],
  "action_items": [{"action": "Action 1", "owner": "Owner 1", "deadline": "2024-01-01"}],
  "next_steps": ["Next step 1", "Next step 2", "Next step 3"]
}
```