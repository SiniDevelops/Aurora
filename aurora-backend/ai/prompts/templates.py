"""Prompt templates."""

NOTE_CREATION_PROMPT = """Create a new note based on the following input.
Format the note nicely in Markdown.

Input: {user_input}
Context: {context}"""

SEARCH_RESULT_PROMPT = """Present the following search results to the user in a clear and concise manner.

Search Results:
{results}

User Request: {user_input}"""

SUMMARIZATION_PROMPT = """Summarize the following text or notes. Highlight the key points.

Content to summarize:
{content}"""

GENERAL_CHAT_PROMPT = """Engage in a helpful conversation with the user.

User: {user_input}
Context: {context}"""
