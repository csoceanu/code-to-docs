import os
import subprocess
import argparse
from pathlib import Path
from google import genai
from google.genai import types

# === CONFIG ===
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
DOCS_REPO_URL = os.environ["DOCS_REPO_URL"]
BRANCH_NAME = "doc-update-from-pr"

def get_diff():
    """Get the full diff for the entire PR, not just the latest commit"""
    # First, try to get PR base from environment (set by GitHub Actions)
    pr_base = os.environ.get("PR_BASE", "origin/main")
    pr_number = os.environ.get("PR_NUMBER", "unknown")
    
    print(f"Getting diff for PR #{pr_number} against base: {pr_base}")
    
    # Get the merge-base to ensure we capture all PR changes
    merge_base_result = subprocess.run(
        ["git", "merge-base", pr_base, "HEAD"], 
        capture_output=True, text=True
    )
    
    if merge_base_result.returncode == 0:
        # Use merge-base to get all changes in the PR branch
        merge_base = merge_base_result.stdout.strip()
        print(f"Using merge-base: {merge_base[:7]}...{merge_base[-7:]}")
        
        # Show which files changed in the entire PR
        files_result = subprocess.run(
            ["git", "diff", "--name-only", f"{merge_base}...HEAD"], 
            capture_output=True, text=True
        )
        if files_result.returncode == 0:
            changed_files = files_result.stdout.strip().split('\n')
            changed_files = [f for f in changed_files if f.strip()]
            print(f"Files changed in entire PR: {changed_files}")
        
        result = subprocess.run(
            ["git", "diff", f"{merge_base}...HEAD"], 
            capture_output=True, text=True
        )
        diff_method = f"merge-base ({merge_base[:7]}...HEAD)"
    else:
        # Fallback to the original method
        print("Warning: Could not find merge-base, using fallback diff method")
        result = subprocess.run(
            ["git", "diff", f"{pr_base}...HEAD"], 
            capture_output=True, text=True
        )
        diff_method = f"direct ({pr_base}...HEAD)"
    
    diff_content = result.stdout.strip()
    print(f"Diff method: {diff_method}")
    print(f"Diff size: {len(diff_content)} characters")
    
    return diff_content

def get_commit_info():
    """Get PR information for the documentation PR reference"""
    try:
        # Get PR number from environment if available
        pr_number = os.environ.get("PR_NUMBER")
        print(f"Debug: PR_NUMBER from environment: '{pr_number}'")
        
        # Get the HEAD commit - this is what GitHub Actions checked out for the PR
        current_commit_result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if current_commit_result.returncode != 0:
            return None
        commit_hash = current_commit_result.stdout.strip()
        
        # Get remote origin URL to construct proper commit links
        remote_url = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True)
        if remote_url.returncode != 0:
            return None
        
        # Convert SSH URL to HTTPS if needed
        repo_url = remote_url.stdout.strip()
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/").replace(".git", "")
        elif repo_url.endswith(".git"):
            repo_url = repo_url.replace(".git", "")
        
        # Get commit details
        short_hash = commit_hash[:7]
        
        # Return PR information if available, otherwise fallback to commit info
        result = {
            'repo_url': repo_url,
            'current_commit': commit_hash,
            'short_hash': short_hash
        }
        
        # Check if we have a valid PR number (not None, not empty, not "unknown")
        if pr_number and pr_number.strip() and pr_number != "unknown":
            result['pr_number'] = pr_number
            result['pr_url'] = f"{repo_url}/pull/{pr_number}"
            print(f"Debug: Using PR info - PR #{pr_number}")
        else:
            print(f"Debug: No valid PR number, falling back to commit info")
        
        return result
            
    except Exception as e:
        print(f"Warning: Could not get commit info: {e}")
        return None

def setup_docs_environment():
    """Set up docs environment - either local subfolder or clone separate repo"""
    docs_subfolder = os.environ.get("DOCS_SUBFOLDER")
    
    if docs_subfolder:
        # Use local subfolder (same repo)
        current_dir = os.getcwd()
        print(f"DEBUG: Current working directory before chdir: {current_dir}")
        print(f"DEBUG: DOCS_SUBFOLDER environment variable value: '{docs_subfolder}'")
        print(f"DEBUG: Full path to docs subfolder: {os.path.join(current_dir, docs_subfolder)}")
        
        if not os.path.exists(docs_subfolder):
            print(f"ERROR: Docs subfolder '{docs_subfolder}' not found at {os.path.join(current_dir, docs_subfolder)}")
            print(f"DEBUG: Contents of current directory: {os.listdir('.')}")
            return False
        
        print(f"DEBUG: Changing to docs subfolder: {docs_subfolder}")    
        os.chdir(docs_subfolder)
        
        final_dir = os.getcwd()
        print(f"DEBUG: Final working directory after chdir: {final_dir}")
        print(f"DEBUG: Contents of docs directory: {os.listdir('.')[:10]}...")  # Show first 10 items
        return True
    else:
        # Clone separate repository (existing behavior)
        print("Cloning separate docs repository")
        subprocess.run(["git", "clone", DOCS_REPO_URL, "docs_repo"])
        os.chdir("docs_repo")

        # Try to check out the branch if it already exists
        result = subprocess.run(["git", "ls-remote", "--heads", "origin", BRANCH_NAME], capture_output=True, text=True)
        if result.stdout.strip():
            print(f"Reusing existing branch: {BRANCH_NAME}")
            subprocess.run(["git", "fetch", "origin", BRANCH_NAME])
            subprocess.run(["git", "checkout", BRANCH_NAME])
            subprocess.run(["git", "pull", "origin", BRANCH_NAME])
        else:
            print(f"Creating new branch: {BRANCH_NAME}")
            subprocess.run(["git", "checkout", "-b", BRANCH_NAME])
        return True


def summarize_long_file(file_path, content):
    """Generate AI summary for the given file content"""
    print(f"Generating summary for long file: {file_path}")
    
    prompt = f"""
Analyze this documentation file and create a comprehensive summary that captures:

1. **Primary Purpose**: What this file documents
2. **Key Topics Covered**: Main sections, features, components discussed  
3. **Technical Keywords**: Important terms, APIs, configuration options, commands
4. **Target Audience**: Who would use this documentation
5. **Related Concepts**: What other systems/features this relates to

File: {file_path}
Content:
{content}

Provide a detailed summary that would help an AI system understand when this file should be updated based on code changes.
"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        ),
    )
    
    return response.text.strip()

def get_file_content_or_summaries(line_threshold=300):
    """Get file content - full content for short files, AI summaries for long files"""
    file_data = []
    # Look for both .adoc and .md documentation files
    doc_files = []
    doc_files.extend(list(Path(".").rglob("*.adoc")))
    doc_files.extend(list(Path(".").rglob("*.md")))
    
    for path in doc_files:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
                
            # Check file length and decide what to use
            line_count = len(content.split('\n'))
            
            if line_count > line_threshold:
                # Long file - generate summary
                content_to_use = summarize_long_file(str(path), content)
                print(f"Processed {path}: {line_count} lines (using AI summary)")
            else:
                # Short file - use full content
                content_to_use = content
                print(f"Processed {path}: {line_count} lines (using full content)")
            
            file_data.append((str(path), content_to_use))
            
        except Exception as e:
            print(f"Skipping file {path}: {e}")
    
    print(f"DEBUG: Returning {len(file_data)} files for processing")
    return file_data

def ask_gemini_for_relevant_files(diff, file_previews):
    all_relevant_files = []
    batch_size = 10
    
    # Process files in batches of 10
    for i in range(0, len(file_previews), batch_size):
        batch = file_previews[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(file_previews) + batch_size - 1) // batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)...")
        
        # Create context for this batch of 10 files
        context = "\n\n".join(
            [f"File: {fname}\nPreview:\n{preview}" for fname, preview in batch]
        )

        prompt = f"""
        You are a VERY STRICT documentation assistant. You must select ONLY the ABSOLUTE MINIMUM files.

        A code change was made in this PR (Git diff):
        {diff}

        Below is a list of documentation files (.adoc and .md) and their content:

        {context}

        STRICT RULES - BE EXTREMELY CONSERVATIVE:
        1. ONLY select command reference files if a command was added/modified
        2. ONLY select feature-specific docs if that EXACT feature was changed
        3. When in doubt, DO NOT select the file

        Based on the diff, which files from this list should be updated? Return only the file paths (one per line). No explanations or extra formatting.
        If no files need updates, return "NONE".
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        
        result_text = response.text.strip()
        if result_text.upper() == "NONE":
            print(f"Batch {batch_num}: No relevant files found")
            continue
        
        # Filter out source code files - only keep documentation files (.adoc and .md)
        suggested_files = [line.strip() for line in result_text.splitlines() if line.strip()]
        filtered_files = [f for f in suggested_files if f.endswith('.adoc') or f.endswith('.md')]
        
        if len(filtered_files) != len(suggested_files):
            skipped = [f for f in suggested_files if not (f.endswith('.adoc') or f.endswith('.md'))]
            print(f"Batch {batch_num}: Skipping non-documentation files: {skipped}")
        
        all_relevant_files.extend(filtered_files)
        print(f"Batch {batch_num}: Found {len(filtered_files)} relevant files")
    
    print(f"Total relevant files found: {len(all_relevant_files)}")
    return all_relevant_files

def load_full_content(file_path):
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return ""

def ask_gemini_for_updated_content(diff, file_path, current_content):
    # Determine file format based on extension
    is_markdown = file_path.endswith('.md')
    is_asciidoc = file_path.endswith('.adoc')
    
    if is_markdown:
        format_instructions = """
CRITICAL FORMATTING REQUIREMENTS FOR MARKDOWN FILES:
**MOST IMPORTANT**: The output must be RAW MARKDOWN content that can be written DIRECTLY to a .md file.
- NEVER wrap the output in code fences like ```markdown or ``` 
- The FIRST character of your response should be the FIRST character of the file (# for header, comment, or text)
- The LAST character of your response should be the LAST character of the file content
- NO "```markdown" at the beginning
- NO "```" at the end
- Return ONLY the raw file content, nothing else
- Use standard Markdown syntax: # for headers, ``` for code blocks within content, | for tables
- Table separators must be simple: |---|---|---| (no backslashes, no extra characters)
- Maintain proper table structures with correct column alignment
- Keep all links and references intact and properly formatted
- Use consistent indentation and spacing
- Do NOT mix AsciiDoc syntax with Markdown
"""
        format_name = "Markdown"
    elif is_asciidoc:
        format_instructions = """
CRITICAL FORMATTING REQUIREMENTS FOR ASCIIDOC FILES:
**MOST IMPORTANT**: The output must be RAW ASCIIDOC content that can be written DIRECTLY to a .adoc file.
- NEVER wrap the output in code fences like ```adoc or ``` or ```asciidoc
- The FIRST character of your response should be the FIRST character of the file
- The LAST character of your response should be the LAST character of the file content
- NO "```adoc" or "```asciidoc" at the beginning
- NO "```" at the end
- Return ONLY the raw file content, nothing else
- Use ONLY AsciiDoc syntax: ==== for headers, |=== for tables, ---- for code blocks
- Do NOT mix markdown and AsciiDoc syntax
- Maintain proper table structures with matching |=== opening and closing
- Keep all cross-references (xref) intact and properly formatted
"""
        format_name = "AsciiDoc"
    else:
        # Default to treating as text/markdown
        format_instructions = """
FORMATTING REQUIREMENTS:
- Maintain the existing format and syntax of the file
- Keep all links and references intact and properly formatted
- Use consistent indentation and spacing
"""
        format_name = "the existing format"

    prompt = f"""
You are a CONSERVATIVE documentation assistant. Only make changes if ABSOLUTELY necessary.

{format_instructions}
- Ensure consistent indentation and spacing

A developer made the following code changes:
{diff}

Here is the full content of the current documentation file `{file_path}`:
--------------------
{current_content}
--------------------

IMPORTANT RULES:
1. First, verify the file's purpose matches the code changes. If the file is about a completely different feature, return `NO_UPDATE_NEEDED`
2. Check if the file already covers the code changes adequately. Most files don't need updates.
3. Only add information that is DIRECTLY related to the code changes shown
4. DO NOT add tangential information just because it seems related
5. DO NOT rewrite or restructure the file - only add/modify what's necessary
6. Preserve all existing content, links, formatting, and structure

DECISION:
- If the file is about a different topic than the code changes → `NO_UPDATE_NEEDED`
- If the file already covers this information adequately → `NO_UPDATE_NEEDED`  
- If truly new, important information is missing → Return updated file content

Return ONLY:
- `NO_UPDATE_NEEDED` (if file doesn't need changes), OR
- The complete updated file in valid {format_name} format (if changes are essential)
"""


    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        ),
    )
    return response.text.strip()

def overwrite_file(file_path, new_content):
    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Failed to write {file_path}: {e}")
        return False

def push_and_open_pr(modified_files, commit_info=None):
    subprocess.run(["git", "add"] + modified_files)
    
    # Build commit message with useful links
    commit_msg = "Auto-generated doc updates from code changes"
    
    if commit_info:
        if 'pr_number' in commit_info:
            commit_msg += f"\n\nPR Link: {commit_info['pr_url']}"
            commit_msg += f"\nLatest commit: {commit_info['short_hash']}"
        else:
            # Fallback to commit reference if no PR info available
            commit_url = f"{commit_info['repo_url']}/commit/{commit_info['current_commit']}"
            commit_msg += f"\n\nCommit Link: {commit_url}"
            commit_msg += f"\nLatest commit: {commit_info['short_hash']}"
    
    commit_msg += "\n\nAssisted-by: Gemini"
    
    subprocess.run([
        "git", "commit",
        "-m", commit_msg
    ])
    
    # Add remote with token auth
    gh_token = os.environ["GH_TOKEN"]
    docs_repo_url = DOCS_REPO_URL.replace("https://", f"https://{gh_token}@")

    # Clear GitHub Actions default authentication that interferes with our PAT
    subprocess.run(["git", "config", "--unset-all", "http.https://github.com/.extraheader"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    subprocess.run(["git", "remote", "set-url", "origin", docs_repo_url])
    subprocess.run(["git", "push", "--set-upstream", "origin", BRANCH_NAME, "--force"])

    # Build PR body (simple, without commit references)
    pr_body = "This PR updates the following documentation files based on code changes:\n\n"
    pr_body += "\n".join([f"- `{f}`" for f in modified_files])
    pr_body += "\n\n*Note: Each commit in this PR contains references to the specific source code commits that triggered the documentation updates.*"

    subprocess.run([
        "gh", "pr", "create",
        "--title", "Auto-Generated Doc Updates from Code PR",
        "--body", pr_body,
        "--base", "master",
        "--head", BRANCH_NAME
    ])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without writing files or pushing PR")
    args = parser.parse_args()

    diff = get_diff()
    if not diff:
        print("No changes detected.")
        return
    # Get commit info before switching to docs repo
    commit_info = get_commit_info()
    if commit_info:
        print(f"Source repository: {commit_info['repo_url']}")
        print(f"Latest commit: {commit_info['short_hash']}")
    
    if not setup_docs_environment():
        print("Failed to set up docs environment")
        return
        
    file_previews = get_file_content_or_summaries()
    print(f"DEBUG: Collected {len(file_previews)} file previews")

    if not file_previews:
        print("No documentation files found to process.")
        return

    print("Asking Gemini for relevant files...")
    relevant_files = ask_gemini_for_relevant_files(diff, file_previews)
    if not relevant_files:
        print("Gemini did not suggest any files.")
        return

    print("Files selected by Gemini:", relevant_files)

    modified_files = []
    for file_path in relevant_files:
        current = load_full_content(file_path)
        if not current:
            continue

        print(f"Checking if {file_path} needs an update...")
        updated = ask_gemini_for_updated_content(diff, file_path, current)

        if updated.strip() == "NO_UPDATE_NEEDED":
            print(f"No update needed for {file_path}")
            continue

        if args.dry_run:
            print(f"[Dry Run] Would update {file_path} with:\n{updated}\n")
        else:
            print(f"Updating {file_path}...")
            if overwrite_file(file_path, updated):
                modified_files.append(file_path)

    if modified_files:
        if args.dry_run:
            print("[Dry Run] Would push and open PR for the following files:")
            for f in modified_files:
                print(f"- {f}")
            
            if commit_info:
                # Show what the commit message would look like
                commit_msg = "Auto-generated doc updates from code changes"
                
                if 'pr_number' in commit_info:
                    commit_msg += f"\n\nPR Link: {commit_info['pr_url']}"
                    commit_msg += f"\nLatest commit: {commit_info['short_hash']}"
                else:
                    # Fallback to commit reference if no PR info available
                    commit_url = f"{commit_info['repo_url']}/commit/{commit_info['current_commit']}"
                    commit_msg += f"\n\nCommit Link: {commit_url}"
                    commit_msg += f"\nLatest commit: {commit_info['short_hash']}"
                
                commit_msg += "\n\nAssisted-by: Gemini"
                
                print(f"\n[Dry Run] Commit message would be:")
                print("=" * 50)
                print(commit_msg)
                print("=" * 50)
                
                print(f"\n[Dry Run] PR body would be simple (commit reference is in commit message only)")
        else:
            # Handle same-repo vs separate-repo scenarios
            docs_subfolder = os.environ.get("DOCS_SUBFOLDER")
            if docs_subfolder:
                print("Same-repo scenario: preparing for PR creation...")
                # Go back to repo root for git operations
                os.chdir("..")
                # Create and switch to docs branch
                subprocess.run(["git", "checkout", "-b", BRANCH_NAME])
                # Convert file paths to include docs subfolder prefix
                docs_files = [f"{docs_subfolder}/{f}" if not f.startswith(docs_subfolder) else f for f in modified_files]
                push_and_open_pr(docs_files, commit_info)
            else:
                print("Separate-repo scenario: creating PR...")
                push_and_open_pr(modified_files, commit_info)
    else:
        print("All documentation is already up to date — no PR created.")

if __name__ == "__main__":
    main()