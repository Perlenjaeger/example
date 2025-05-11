import os
import subprocess
import requests

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
PR_NUMBER = os.environ['PR_NUMBER']
BASE_REF = os.environ['BASE_REF']
HEAD_REF = os.environ['HEAD_REF']
REPO = os.environ['GITHUB_REPOSITORY']
AI_API_URL = "https://api.openai.com/v1/chat/completions"
AI_API_KEY = os.environ['AI_API_KEY']

def get_diff(base_ref, head_ref):
    try:
        result = subprocess.run(['git', 'diff', base_ref, head_ref], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting diff: {e}")
        return None

def call_ai_review(diff_content):
    prompt = f"""Review the following code changes in diff format.\nIdentify severe code smells, potential bugs, performance issues, or maintainability problems.\nAlso, evaluate if these changes likely require an update to the README.md file.\nProvide your findings in a structured format, preferably JSON.\n\nCode Diff:\n```diff\n{diff_content}\n```"""
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
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling AI API: {e}")
        return None

def post_pr_comment(repo, pr_number, comment_body):
    url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": comment_body}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print("Comment posted successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment: {e}")

def main():
    diff = get_diff(BASE_REF, HEAD_REF)
    if not diff:
        post_pr_comment(REPO, PR_NUMBER, "Review bot failed to get diff.")
        exit(1)

    ai_response = call_ai_review(diff)
    if not ai_response:
        post_pr_comment(REPO, PR_NUMBER, "Review bot failed to get response from AI API.")
        exit(1)

    ai_response_text = ai_response.get('choices', [{}])[0].get('message', {}).get('content', 'No AI response content.')
    post_pr_comment(REPO, PR_NUMBER, ai_response_text)

if __name__ == "__main__":
    main()