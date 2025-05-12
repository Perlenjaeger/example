import os
import subprocess
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for API URLs
GITHUB_API_URL = "https://api.github.com"
AI_API_URL = "https://api.openai.com/v1/chat/completions"

# Environment variables for sensitive data
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
PR_NUMBER = os.environ.get('PR_NUMBER')
BASE_REF = os.environ.get('BASE_REF')
HEAD_REF = os.environ.get('HEAD_REF')
REPO = os.environ.get('GITHUB_REPOSITORY')
AI_API_KEY = os.environ.get('AI_API_KEY')

if not all([GITHUB_TOKEN, PR_NUMBER, BASE_REF, HEAD_REF, REPO, AI_API_KEY]):
    logging.error("One or more required environment variables are missing.")
    exit(1)

def get_diff(base_ref, head_ref):
    """Get the git diff between two references."""
    try:
        result = subprocess.run(['git', 'diff', base_ref, head_ref], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting diff: {e}")
        return None

def call_ai_review(diff_content):
    """Send the code diff to the AI API for review and return the response."""
    prompt = f"""Review the following code changes in diff format.
Identify severe code smells, potential bugs, performance issues, or maintainability problems.
Also, evaluate if these changes likely require an update to the README.md file.
Provide your findings in Markdown format.

Code Diff:
```diff
{diff_content}
```"""
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(AI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        return response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling AI API: {e}")
        return None

def post_pr_comment(repo, pr_number, comment_body):
    """Post a comment on the pull request."""
    url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": comment_body}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logging.info("Comment posted successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error posting comment: {e}")

def main():
    """Main function to orchestrate the review process."""
    diff = get_diff(BASE_REF, HEAD_REF)
    if not diff:
        post_pr_comment(REPO, PR_NUMBER, "Review bot failed to get diff.")
        exit(1)

    ai_response = call_ai_review(diff)
    if not ai_response:
        post_pr_comment(REPO, PR_NUMBER, "Review bot failed to get response from AI API.")
        exit(1)

    ai_response_text = ai_response.strip() if isinstance(ai_response, str) else "No findings found."
    if not ai_response_text:
        ai_response_text = "No findings found."

    post_pr_comment(REPO, PR_NUMBER, ai_response_text)

if __name__ == "__main__":
    main()
